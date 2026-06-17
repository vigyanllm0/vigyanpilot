-- =============================================================
-- 005: Triggers — Business Logic & Security Enforcement
-- =============================================================

-- -----------------------------------------------------------
-- A. Auto-update `updated_at` on users table
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_timestamp();


-- -----------------------------------------------------------
-- B. Auto-calculate margin on cost_ledger INSERT
-- Computes gross_margin and margin_percent automatically
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_calculate_margins()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate total COGS
    NEW.total_cogs_inr := NEW.infra_cost_inr + NEW.llm_cost_inr + NEW.external_api_cost_inr;
    
    -- Calculate gross margin
    NEW.gross_margin_inr := NEW.revenue_inr - NEW.total_cogs_inr;
    
    -- Calculate margin percentage (avoid division by zero)
    IF NEW.revenue_inr > 0 THEN
        NEW.margin_percent := ((NEW.revenue_inr - NEW.total_cogs_inr) / NEW.revenue_inr) * 100;
    ELSE
        NEW.margin_percent := -100.00;  -- Pure cost, no revenue (admin/free usage)
    END IF;
    
    -- Auto-detect billing method based on user role
    IF EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id AND role = 'admin') THEN
        NEW.is_billable := FALSE;
        NEW.billing_method := 'admin_free';
        NEW.revenue_inr := 0;
        NEW.gross_margin_inr := 0 - NEW.total_cogs_inr;
        NEW.margin_percent := -100.00;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cost_ledger_margins
    BEFORE INSERT ON cost_ledger
    FOR EACH ROW
    EXECUTE FUNCTION fn_calculate_margins();


-- -----------------------------------------------------------
-- C. Update user lifetime totals when cost_ledger gets a new entry
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_update_user_lifetime_totals()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE token_balances
    SET lifetime_cogs_inr = lifetime_cogs_inr + NEW.total_cogs_inr,
        lifetime_revenue_inr = lifetime_revenue_inr + NEW.revenue_inr
    WHERE user_id = NEW.user_id;
    
    -- If no row exists, create one
    IF NOT FOUND THEN
        INSERT INTO token_balances (user_id, lifetime_cogs_inr, lifetime_revenue_inr)
        VALUES (NEW.user_id, NEW.total_cogs_inr, NEW.revenue_inr)
        ON CONFLICT (user_id) DO UPDATE SET
            lifetime_cogs_inr = token_balances.lifetime_cogs_inr + NEW.total_cogs_inr,
            lifetime_revenue_inr = token_balances.lifetime_revenue_inr + NEW.revenue_inr;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_lifetime_totals
    AFTER INSERT ON cost_ledger
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_user_lifetime_totals();


-- -----------------------------------------------------------
-- D. Payment Status Monotonicity
-- Prevents backward status transitions on payments table.
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_enforce_payment_status_transition()
RETURNS TRIGGER AS $$
DECLARE
    valid BOOLEAN := FALSE;
BEGIN
    IF OLD.status = 'initiated' AND NEW.status IN ('authorized', 'failed') THEN
        valid := TRUE;
    ELSIF OLD.status = 'authorized' AND NEW.status IN ('captured', 'failed') THEN
        valid := TRUE;
    ELSIF OLD.status = 'captured' AND NEW.status = 'refunded' THEN
        valid := TRUE;
    ELSIF OLD.status = NEW.status THEN
        valid := TRUE;
    END IF;

    IF NOT valid THEN
        RAISE EXCEPTION 'Invalid payment status transition: % → %', OLD.status, NEW.status;
    END IF;

    IF NEW.status = 'authorized' AND OLD.status != 'authorized' THEN
        NEW.authorized_at := NOW();
    ELSIF NEW.status = 'captured' AND OLD.status != 'captured' THEN
        NEW.captured_at := NOW();
    ELSIF NEW.status = 'failed' AND OLD.status != 'failed' THEN
        NEW.failed_at := NOW();
    ELSIF NEW.status = 'refunded' AND OLD.status != 'refunded' THEN
        NEW.refunded_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payment_status_transition
    BEFORE UPDATE ON payments
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION fn_enforce_payment_status_transition();


-- -----------------------------------------------------------
-- E. Auto-create revenue_ledger entry when payment is captured
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_record_revenue_on_capture()
RETURNS TRIGGER AS $$
DECLARE
    gateway_fee NUMERIC(10, 4);
    gst_on_fee NUMERIC(10, 4);
    net_rev NUMERIC(12, 4);
    cost_per_token NUMERIC(8, 4);
BEGIN
    -- Only fire when status transitions TO 'captured'
    IF NEW.status = 'captured' AND OLD.status != 'captured' THEN
        -- Razorpay fee: ~2% + GST (18% on the fee)
        gateway_fee := NEW.amount * 0.02;
        gst_on_fee := gateway_fee * 0.18;
        net_rev := NEW.amount - gateway_fee - gst_on_fee;
        
        -- Cost per token for this purchase
        IF NEW.tokens_purchased > 0 THEN
            cost_per_token := NEW.amount / NEW.tokens_purchased;
        ELSE
            cost_per_token := 0;
        END IF;
        
        INSERT INTO revenue_ledger (
            user_id, payment_id, revenue_type, product_id,
            gross_amount_inr, gateway_fee_inr, gst_amount_inr,
            net_revenue_inr, tokens_credited, cost_per_token_to_user
        ) VALUES (
            NEW.user_id,
            NEW.id,
            COALESCE(NEW.product_type, 'unknown'),
            COALESCE(NEW.product_type, 'unknown'),
            NEW.amount,
            gateway_fee,
            gst_on_fee,
            net_rev,
            COALESCE(NEW.tokens_purchased, 0),
            cost_per_token
        );
        
        -- Update user lifetime revenue in token_balances
        UPDATE token_balances
        SET lifetime_revenue_inr = lifetime_revenue_inr + net_rev
        WHERE user_id = NEW.user_id;
        
        IF NOT FOUND THEN
            INSERT INTO token_balances (user_id, lifetime_revenue_inr)
            VALUES (NEW.user_id, net_rev)
            ON CONFLICT (user_id) DO UPDATE SET
                lifetime_revenue_inr = token_balances.lifetime_revenue_inr + net_rev;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_revenue_on_payment_capture
    AFTER UPDATE ON payments
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION fn_record_revenue_on_capture();


-- -----------------------------------------------------------
-- F. Account Lockout after N failed logins
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_track_failed_logins()
RETURNS TRIGGER AS $$
DECLARE
    recent_failures INTEGER;
BEGIN
    IF NEW.result != 'success' THEN
        SELECT COUNT(*) INTO recent_failures
        FROM login_logs
        WHERE user_id = NEW.user_id
          AND result != 'success'
          AND logged_at > NOW() - INTERVAL '15 minutes';

        IF recent_failures >= 4 THEN
            UPDATE users
            SET locked_until = NOW() + INTERVAL '30 minutes',
                failed_login_count = failed_login_count + 1
            WHERE id = NEW.user_id;

            INSERT INTO system_events (severity, module, message, context)
            VALUES (
                'WARNING',
                'auth',
                'Account locked due to repeated failed login attempts',
                jsonb_build_object(
                    'user_id', NEW.user_id,
                    'ip_address', NEW.ip_address::TEXT,
                    'failures_in_window', recent_failures + 1
                )
            );
        END IF;
    ELSE
        UPDATE users
        SET failed_login_count = 0, locked_until = NULL
        WHERE id = NEW.user_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_track_failed_logins
    AFTER INSERT ON login_logs
    FOR EACH ROW
    EXECUTE FUNCTION fn_track_failed_logins();


-- -----------------------------------------------------------
-- G. Audit Trail — Track sensitive changes
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_trail (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW),
                current_setting('app.current_user', TRUE));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_trail (table_name, record_id, action, old_values, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', to_jsonb(OLD),
                current_setting('app.current_user', TRUE));
        RETURN OLD;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_trail (table_name, record_id, action, new_values, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', to_jsonb(NEW),
                current_setting('app.current_user', TRUE));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_payments
    AFTER INSERT OR UPDATE OR DELETE ON payments
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trail();

CREATE TRIGGER trg_audit_revenue
    AFTER INSERT ON revenue_ledger
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trail();

CREATE TRIGGER trg_audit_cost_ledger
    AFTER INSERT ON cost_ledger
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trail();

-- Audit user role/status/email changes only
CREATE OR REPLACE FUNCTION fn_audit_user_sensitive()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.role IS DISTINCT FROM NEW.role
       OR OLD.status IS DISTINCT FROM NEW.status
       OR OLD.email IS DISTINCT FROM NEW.email THEN
        INSERT INTO audit_trail (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES ('users', OLD.id, 'UPDATE',
                jsonb_build_object('role', OLD.role, 'status', OLD.status, 'email', OLD.email),
                jsonb_build_object('role', NEW.role, 'status', NEW.status, 'email', NEW.email),
                current_setting('app.current_user', TRUE));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_users_sensitive
    AFTER UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_audit_user_sensitive();


-- -----------------------------------------------------------
-- H. Immutable tables — Prevent UPDATE/DELETE
-- -----------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_prevent_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '% operations are not permitted on table %', TG_OP, TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_webhooks_immutable
    BEFORE UPDATE OR DELETE ON gateway_webhooks
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_mutation();

CREATE TRIGGER trg_audit_immutable
    BEFORE UPDATE OR DELETE ON audit_trail
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_mutation();

CREATE TRIGGER trg_revenue_immutable
    BEFORE UPDATE OR DELETE ON revenue_ledger
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_mutation();

CREATE TRIGGER trg_cost_ledger_immutable
    BEFORE UPDATE OR DELETE ON cost_ledger
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_mutation();
