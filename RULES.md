# RULES.md — VigyanLLM Website Standards

**Structure & precedence (adopted 2026-10-02):**

- **Part 1 (GOVERNING):** *VigyanLLM Website Rules: Human-First Content, Design, and Review* — the non-negotiable acceptance standard for every public page, component, graphic, metadata block, and interactive element.
- **Part 2 (subsidiary):** the original writing/layout/design guidance below. Where Part 2 conflicts with Part 1, **Part 1 wins.** Sections marked `⛔ RETIRED` are superseded (notably detector-evasion tactics, prohibited by Human-First rule #4) and **must not be followed**.
- Enforcement: run `python3 scripts/rules_lint.py` plus the pre-publish checklist in Part 1 §10 before any publish/deploy.

---

# PART 1 — GOVERNING: Human-First Content, Design, and Review

# VigyanLLM Website Rules: Human-First Content, Design, and Review

**Purpose:** Make every VigyanLLM page and component feel specific, credible, useful, and cared for by real people with relevant expertise. These rules apply to the homepage, product and tool pages, scientific articles, glossary, pricing, partnership, sales, support, graphics, photography, animation, metadata, and interactive components.

**Interpretation of “human-generated”:** Do not try to disguise AI use or fool AI detectors. Build authentic human-led work: original insight, real evidence, responsible ownership, accurate product behavior, and thoughtful design. No style trick can guarantee that a page will be perceived as human or rank well. Google’s published guidance focuses on usefulness, originality, accuracy, trust, and page experience—not on making text evade a detector. [1] [2] [6]

## 1. Non-negotiable rules

1. **A named human owns every public page.** The owner is accountable for accuracy, usefulness, updates, and corrections even when AI helped with research, drafts, translation, code, or visuals.
2. **A qualified human reviews the substance.** Scientific, bioinformatics, clinical, privacy, security, legal, pricing, and performance claims must be checked by someone qualified in that subject before publication.
3. **Never fake human involvement.** Do not invent an author, reviewer, credential, lab, experiment, customer, partner, quote, testimonial, award, institution, number of users, or first-hand experience.
4. **Never try to beat AI detectors.** Do not add deliberate errors, awkward sentences, invisible characters, synonym substitutions, random personal anecdotes, or false bylines to make AI-assisted material look human.
5. **Do not publish unreviewed AI output.** AI can help research or structure original work, but every generated factual claim, title, description, image alternative, structured-data field, translation, and code sample must be checked before release. [2]
6. **Do not publish for volume alone.** Every page must serve a real audience and a distinct purpose. Thin pages produced at scale, copied or lightly rewritten material, doorway pages, keyword stuffing, and search-engine-first pages are prohibited. [1] [3]
7. **Do not imply evidence that does not exist.** Label illustrations, examples, simulations, and concept UI clearly. Never present generated images or invented interface states as product screenshots, lab results, or customer evidence.
8. **Do not promise rankings, traffic, leads, revenue, safety, clinical performance, or scientific outcomes.** State what has been measured, for which sample and period, and what remains unknown.
9. **Accessibility is part of the design definition.** A polished visual is not ready if users cannot read, navigate, understand, or operate it.
10. **No material website changes are complete until verified on the published page.** A mockup, AI-generated visual, audit recommendation, or local draft is not a live implementation.

## 2. Google guidance: what it says and what it does not say

- Google says generative AI may help with research and structuring original content. Using AI is not automatically a violation; generating many low-value pages primarily to manipulate search is the risk. [2] [3]
- Google recommends checking automatically generated material for accuracy, quality, and relevance. It specifically notes that fact-checking also applies to titles, descriptions, structured data, and image alt text. [2]
- Google says information about how content was created can give readers useful context. Disclose AI assistance when it materially affects trust or when readers would reasonably want to know; do not claim that Google requires an AI label on every page. [2]
- Google describes people-first content as work made primarily to help an intended audience, supported by expertise and enough substance to satisfy the reader. It warns against producing lots of pages across unrelated topics, summarizing others without adding value, changing dates without substantial updates, and writing to an imagined preferred word count. [1]
- Google says E-E-A-T itself is not a single specific ranking factor. Use experience, expertise, authority, and trust as editorial quality questions, not as a scoring badge or ranking guarantee. Trust is the central consideration in Google’s explanation. [1]
- Google’s page-experience guidance calls for an overall good experience across mobile display, secure delivery, intrusive overlays, content clarity, and Core Web Vitals. Google also says there is no single page-experience signal and that a good score does not guarantee top rankings. [6]

**Our standard is stricter than minimum search compliance:** original human review, substantiated scientific claims, honest product descriptions, inclusive design, and transparent corrections are required whether or not they affect rankings.

## 3. Content that shows real expertise

### Before writing

- State the intended reader, the question or task the page answers, and the next useful action.
- Keep each page to one primary purpose. A primer-design guide should not turn into a general AI-company pitch halfway through.
- Confirm that VigyanLLM has a legitimate reason to publish the page: a real tool, an original workflow, a useful explanation, tested guidance, or a clear institutional offering.
- Search the existing site for overlapping pages first. Merge, redirect, or differentiate overlapping intent instead of spinning up another near-duplicate page. Google says duplicate content is not automatically a spam violation, but can confuse users and waste crawl resources. [4]

### While writing

- Answer the reader’s main question early. Use plain, direct language and explain necessary terms when they first appear.
- Add something specific that a competent reader cannot get from a superficial summary: a documented workflow, comparison method, annotated example, reproducible settings, failure case, decision rule, or original analysis.
- Use natural sentence length and precise nouns. Remove generic openings, repeated marketing filler, vague claims such as “revolutionary” or “cutting edge,” and empty paragraphs that could be pasted onto any company’s site.
- Do not manufacture a conversational tone with slang, forced anecdotes, rhetorical questions, or deliberate grammar mistakes. Human quality comes from judgment and specificity, not artificial quirks.
- Use headings to help a reader scan. Do not write to a target word count or repeat the same section template just to make pages appear substantial. [1] [4]
- Explain meaningful limitations beside the claim or instruction they qualify. Do not bury important limitations only in the footer or Terms.
- Keep published language consistent with the actual product version, available tools, deployment modes, pricing, support, and eligibility.

### Authors and review history

- Use a real byline when authorship matters. Link the byline to a truthful biography, role, relevant qualifications, and other work. Do not create fictional experts or anonymous “research teams” for authority.
- Show a review date and reviewer only when a real review took place. Keep the original publication date; change the update date only after a substantive review or change. Google warns against changing dates merely to make unchanged pages appear fresh. [1]
- Maintain an internal change record: page owner, subject reviewer, sources checked, product/version checked, date, changes made, and next review date.
- If AI assistance materially shaped a scientific explanation, analysis, translation, or visual, provide reader context when that helps the audience assess provenance. Never claim “written entirely by a human” unless that statement is true. [2]

## 4. Scientific, biomedical, and product-truth rules

VigyanLLM serves biomedical and research audiences. Errors and exaggerated claims can affect scientific work and institutional decisions, so use a higher evidence standard than ordinary marketing copy.

- For every quantitative or comparative claim, record the source, method, assumptions, scope, sample or dataset, comparator, metric, uncertainty, limitations, software/database version, and date. Link the primary source or reproducible evidence near the claim.
- Separate **what the website says**, **what the product currently does**, **what has been tested**, **what independent sources establish**, and **what is still unknown**. Do not present these as interchangeable.
- Do not use “validated,” “accurate,” “clinical-grade,” “diagnostic,” “regulatory-ready,” “audit-ready,” “secure,” “DPDP-compliant,” “zero data egress,” “air-gapped,” or similar absolute language without current evidence and approval from the responsible scientific, security, legal, or privacy owner.
- Describe computational output as computational output. Preserve research-use-only and independent experimental-validation limits. Do not suggest that in-silico output establishes clinical utility, a diagnosis, therapeutic efficacy, or patient-care suitability.
- Show the release state of each capability truthfully: **available**, **beta/experimental**, **planned**, or **not available**. Use the same state in navigation, articles, pricing, sales material, and partnership pages.
- Never invent benchmark results, citations, data provenance, sample sizes, partner names, user counts, institutional adoption, or customer outcomes.
- For worked examples, identify the input provenance, versions, settings, method, and output needed for a reader to reproduce the example. Clearly label synthetic or illustrative data.
- Before a sequence, structure, or other research input is submitted, explain what is processed, where, by whom, retention/deletion, third-party services, and the relevant support path. These statements must match the verified architecture; do not infer privacy guarantees from product branding.
- Show supported inputs, units, constraints, expected processing time only when measured, validation errors, failure/retry behavior, and export semantics. Never make a button or page promise functionality that is not actually delivered.

### Known VigyanLLM reconciliation items

The prior route audit identified conflicts in public claims about on-premises versus cloud processing, no external APIs versus named outside services, privacy/compliance wording, scientific validation, clinical terminology, and whether some capabilities are live or “coming soon.” These are **publication blockers** for related claims. Resolve each with the appropriate product, architecture, security, privacy, scientific, and legal owners before strengthening the marketing language. See the [audit report](/home/ubuntu/vigyanllm_audit_report.md) and [detailed route appendix](/home/ubuntu/vigyanllm_route_by_route_appendix.md).

## 5. Rules for each website component

### Homepage and landing pages

- Lead with the actual audience and task, not generic “AI will transform everything” language.
- State what the product does now, who it is for, what is research-only, and which next step the visitor can take.
- Choose one primary CTA per page. Make secondary actions genuinely secondary and label them by outcome.
- Show methods, versioning, limitations, and data-handling information close to the claims and tools they explain.
- Use a focused product preview only if it reflects real capabilities; mark a static design concept as **Concept preview**.

### Product and tool interfaces

- Use meaningful labels, examples, units, help text, keyboard-visible focus, input limits, progress, results, and recovery states.
- Distinguish example inputs from user data. Never place real or sensitive sequence/health data in a mockup, demo, analytics event, or support screenshot without explicit authorization and safeguards.
- Put research-use limits and relevant data-flow disclosures before the user submits an input, not only after a result.
- Ensure loading, empty, validation, error, cancellation, and completed states are all designed and tested. Do not invent a “success” state for a feature that is unavailable.
- Keep critical status information readable without color alone, animation, hover, or sound.

### Scientific graphics, diagrams, and data visualization

- Use diagrams to explain a real concept or workflow. Label inputs, methods, units, version/date, and what the diagram does not establish.
- Label a conceptual, generated, or simulated image **Illustrative** or **Concept** when a visitor might mistake it for experimental evidence or a real product result.
- Do not use decorative molecular graphics to imply scientific validation. Do not turn an unverified model output into a polished “result” visual.
- Every chart must use the underlying data faithfully, identify the denominator and source, and avoid decorative distortion. Never use AI image generation for a chart that must preserve exact numerical values.
- Use captions for context and alt text for equivalent meaning. Decorative graphics should have empty alt text so they do not burden screen-reader users.

### Photography and video

- Prefer original, permissioned lab or team photographs where they add genuine context. Record photographer/source, usage rights, date, and consent where relevant.
- Do not use generic stock microscopy, AI-generated scientists, fake lab scenes, or fabricated team portraits as evidence of VigyanLLM’s facilities, staff, experiments, or customers.
- If a stock or generated image is used decoratively, do not let it imply a real experiment, institution, partner, or result. Caption it when the distinction may not be obvious.
- Add captions or transcripts for meaningful video/audio. Provide a clear pause/stop control for motion that can distract or interfere with reading.
- Optimize images for their actual display size; preserve descriptive filenames, relevant placement, responsive sources with a fallback `src`, and useful alt text. Do not keyword-stuff alt text. [5]

### Motion and animation

- Animation must explain a state change, spatial relationship, or interaction. Every animation must have a static equivalent that communicates the same information.
- Keep motion subtle, short, and nonessential. Never use flashing, perpetual motion, autoplay sound, parallax, or animated backgrounds to simulate scientific activity or create urgency.
- Honor the operating system’s reduced-motion preference. Disable or substantially reduce nonessential transitions, smooth scrolling, parallax, and looping animation when reduced motion is requested.
- Do not communicate results, errors, progress, or availability through motion or color alone.
- Check that animations do not delay reading, move content under the user, cause layout shifts, hide focus, or harm mobile performance. WCAG 2.2 contains specific requirements for moving content and an AAA criterion concerning animation from interactions; choose the most inclusive behavior rather than relying only on the minimum conformance level. [7]

### Navigation, consent, forms, pricing, and trust pages

- Use predictable navigation names and meaningful link text. Links should tell visitors what they will find. [4]
- Avoid menus that are overloaded with unrelated tool links. Group pages by user task and keep route, breadcrumb, title, and visible heading consistent.
- Cookie and privacy controls must not obscure the heading, CTA, form, or focused element. Provide equally clear choices to accept, reject optional tracking, and manage preferences; make choices persistent and reversible.
- Explain price, billing period, limits, renewal, cancellation, refund terms, eligibility, and what happens after a CTA before asking for payment or sensitive information.
- Show contact, support, company identity, privacy, terms, and correction paths accurately. Do not use faux trust badges or invented partner logos.

## 6. Accessibility and page experience baseline

Target **WCAG 2.2 AA** for public pages and interactive tools, subject to applicable legal requirements. WCAG is a W3C standard; Google’s page-experience guidance separately emphasizes mobile display, secure delivery, useful content visibility, avoidance of intrusive overlays, and Core Web Vitals. [6] [7]

- Use semantic headings, landmarks, buttons, labels, table headers, and status announcements. Preserve a logical reading and keyboard order.
- All functionality must be keyboard-operable. Focus must be visible and not hidden behind a sticky banner or modal.
- Meet WCAG 2.2 AA contrast requirements: normal text at least 4.5:1, and large text at least 3:1. Do not use color as the sole status indicator. [7]
- Provide meaningful text alternatives for informative images, diagrams, icons, and controls. Leave purely decorative images out of the accessibility tree. [5] [7]
- Support mobile reflow and browser zoom without loss of content or functionality. Prevent clipped navigation, horizontal page overflow, tiny touch targets, and text embedded only in images. WCAG 2.2 AA includes a 24-by-24 CSS pixel minimum target-size criterion with defined exceptions. [7]
- Caption prerecorded video and provide transcripts when the audio conveys meaningful information. [7]
- Respect reduced motion and make motion-dependent content pausable or avoid relying on it. Test using keyboard only, a screen reader, zoom, and a narrow viewport.
- Reserve image and media dimensions to reduce layout shifts. Measure Core Web Vitals with real user data when available; use lab tests to diagnose, not to claim a guaranteed ranking outcome. [6]

## 7. Search, metadata, and structured data

- Publish useful content in the initial HTML for public routes. Add browser interactivity without making the main page content inaccessible to visitors or crawlers. [8]
- Give each indexable route a distinct title, concise description, visible main heading, canonical URL, and relevant social preview that accurately describe the page. [4] [8]
- Use concise, descriptive URLs and a browseable internal-link structure. Consolidate overlapping intent with redirects or canonicals where appropriate. [4]
- Write descriptive link text and place links where they help a reader verify or continue learning. Do not buy, automate, or exchange links to manipulate rankings. [3] [4]
- Use structured data only when it accurately represents visible page content and meets Google’s current feature-specific policies. Validate it and remove it when the underlying content is no longer true. [2]
- Do not use hidden text, cloaking, doorway pages, scraped rewrites, mass-produced location variants, fake freshness, unnatural keyword repetition, or copied competitor content. [1] [3] [4]
- Write image filenames and alt text for people and context, not as keyword containers. Place images near relevant copy. [5]
- Do not publish more content merely because an SEO tool suggests a word count, keyword density, or a large volume of pages. Google explicitly says it has no preferred word count. [1]
- Treat Search Console impressions, clicks, CTR, conversions, and revenue as different metrics. Define the source, denominator, attribution window, bot treatment, privacy safeguards, and baseline before running growth experiments.

## 8. Human review and release workflow

A page is not publish-ready until the following checks are complete:

1. **Owner:** A real person is named internally as accountable for the page.
2. **Purpose:** The intended reader and task are explicit; the page adds distinct value not already available on another VigyanLLM route.
3. **Source check:** Every material claim has a current, relevant source or a clearly documented internal test. Primary sources are preferred.
4. **Scientific check:** A qualified reviewer verifies terminology, calculations, versions, examples, methods, uncertainty, limits, and the research-only boundary.
5. **Product check:** The live capability, user flow, release state, supported inputs, outputs, and pricing match the copy and screenshots.
6. **Data-flow check:** Product, privacy, and security owners confirm deployment, processing, telemetry, processors, retention, and deletion language.
7. **Copy check:** An editor removes filler, repeated passages, vague claims, grammar errors, inaccessible jargon, and unsubstantiated superlatives.
8. **AI-use check:** A human fact-checks all AI-assisted text, code, metadata, alt text, translations, and visual labels. Add user-facing context where it helps readers understand material automation. [2]
9. **Visual check:** Design, illustration, photography, captions, provenance, permissions, and mobile crop are reviewed. Concept imagery is labeled.
10. **Accessibility check:** Keyboard navigation, focus, contrast, zoom/reflow, touch targets, screen-reader labels, captions, and reduced motion pass the team’s WCAG 2.2 AA checklist. [7]
11. **SEO check:** The page answers one real intent, has accurate metadata, helpful internal links, valid canonical/indexing behavior, and no spam tactic. [1] [3] [4]
12. **Post-publish check:** Verify the public page on desktop and mobile, check links and forms, confirm status/metadata, and record the release date and owner.

For high-risk claims, require a second reviewer from the relevant scientific, legal, security, or privacy function. Set a review date based on how quickly the evidence, software, or policy can change.

## 9. Red flags that require a human rewrite or removal

Pause publication when a page has any of these signs:

- It could be moved to any competitor’s website by changing only the company name.
- Its structure, examples, conclusions, and phrasing repeat across several URLs without page-specific value.
- It summarizes other sources but contributes no tested workflow, original analysis, useful synthesis, or better explanation.
- Its author, reviewer, credentials, experiments, citations, users, benchmarks, or visuals cannot be verified.
- It promises clinical, privacy, security, sovereignty, accuracy, or commercial outcomes without evidence and scope.
- The headline promises an answer that the content does not deliver.
- It was published or refreshed because of a trend, search-volume target, or arbitrary word count rather than user need.
- It shows a stock/generated scientist, laboratory, result, or product screen as if it were real.
- It hides limits, uses a blocking consent banner, clips on mobile, has inaccessible contrast, or makes content depend on animation.
- Its tool, pricing, release state, or data-flow claims conflict with other public pages.

The remedy is to substantiate, narrow, rewrite, merge, label, or remove the affected material—not to “humanize” its wording for detection tools.

## 10. Practical approval checklist

Before any page, component, campaign, image, or animation goes live, the owner should be able to answer **yes** to these questions:

- Can we name the real audience and their task?
- Does this route add something useful and distinct?
- Is there a real human owner and a qualified reviewer where needed?
- Can we show where the important claims came from?
- Are product capability, release state, price, and data handling accurate today?
- Are examples and visuals authentic or clearly labeled as illustrative?
- Can a reader understand limitations without searching another page?
- Does the page work on mobile, by keyboard, at zoom, and with reduced motion?
- Are the title, description, links, alt text, and structured data accurate and natural?
- Would we be comfortable explaining the page’s evidence and review history to a researcher, customer, regulator, or journalist?

If any answer is “no,” hold publication and assign an owner to resolve it. **Do not use an AI-detector score as an approval criterion.**

## References

[1]: https://developers.google.com/search/docs/fundamentals/creating-helpful-content "Google Search Central: Creating Helpful, Reliable, People-First Content"
[2]: https://developers.google.com/search/docs/fundamentals/using-gen-ai-content "Google Search Central: Guidance on Using Generative AI Content on Your Website (updated October 1, 2026)"
[3]: https://developers.google.com/search/docs/essentials/spam-policies "Google Search Essentials: Spam Policies"
[4]: https://developers.google.com/search/docs/fundamentals/seo-starter-guide "Google Search Central: SEO Starter Guide"
[5]: https://developers.google.com/search/docs/appearance/google-images "Google Search Central: Google Images SEO Best Practices"
[6]: https://developers.google.com/search/docs/appearance/page-experience "Google Search Central: Understanding Page Experience in Google Search Results"
[7]: https://www.w3.org/TR/WCAG22/ "W3C: Web Content Accessibility Guidelines (WCAG) 2.2"
[8]: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics "Google Search Central: JavaScript SEO Basics"

---

# PART 2 — Style & Design Guidelines (subsidiary)

**Evidence basis:** Georgiou (2026) rapid review of 40 empirical studies on AI vs. human text cues. Five cue families: surface, discourse/pragmatic, epistemic/content, predictability/probabilistic, provenance. Stability is conditional — cues work within genres but break across registers and under paraphrasing. No single marker is reliable; triangulation across families is required.

---

## 1. WRITING STYLE — Sound Like a Person

### DO
- Use contractions: "don't", "can't", "you'll", "we've", "it's"
- Start sentences with "But", "So", "And" occasionally (humans do this)
- Use first person: "We built this because...", "I ran into this problem..."
- Vary sentence length wildly — mix 6-word sentences with 30-word ones
- Include personal opinions: "Honestly, most researchers overthink this."
- Add real caveats: "This works in practice, though purists will argue about it."
- Use informal transitions: "Here's the thing.", "Turns out...", "The trick is..."
- Reference real experiences: "When we were validating primers, we noticed..."
- Include parenthetical asides (like this one) that break the flow
- Use specific, concrete numbers instead of round ones: "127 participants" not "about 130"

### DON'T
- Use "Furthermore", "Moreover", "In conclusion", "It is important to note"
- Use "Delve into", "Harness", "Leverage", "Unlock", "Navigate"
- Use "Whether you're X, Y, or Z" as an opening pattern
- Use "In today's rapidly evolving landscape"
- Write every paragraph as exactly 2-3 sentences
- End every section with a summary sentence
- Use "comprehensive", "robust", "cutting-edge", "seamless", "powerful"
- Write subject-verb-object sentences exclusively
- Use passive voice more than 20% of the time
- Make every paragraph the same length

### Sentence Length Variance (Burstiness)
AI text is predictable. Humans mix short, punchy fragments with longer, clause-heavy sentences. Aim for a burstiness score that looks like natural speech:

```
Good (human-like):
"We ran the t-test. Got p = 0.03, which was right on the edge of significance — 
frankly, I wouldn't trust it without looking at the effect size too. Cohen's d 
came out to 0.18. Tiny. Not clinically meaningful at all."

Bad (AI-generated):
"The t-test yielded a p-value of 0.03, which is below the conventional 
significance threshold of 0.05. However, the effect size (Cohen's d = 0.18) 
was small, indicating that the practical significance of this finding is limited."
```

---

## 1B. DISCOURSE/PRAGMATIC CUES — How You Frame Things

This is the #2 cue family after surface cues. These are about **rhetorical packaging** — how ideas are positioned, how the author signals stance, how the text guides the reader. AI text is fluent but lacks genuine rhetorical posture.

### DO
- **Signal stance with uncertainty markers**: "We think this matters because...", "Honestly, this is probably overkill for most labs", "Our data suggests this — but we haven't tested it on plant sequences yet"
- **Use metadiscourse that guides the reader**: "Here's what most people miss about primer dimers", "If you've ever wondered why BLAST gives you 50 hits for a 20-mer — this is why"
- **Vary disciplinary register**: Bioinformatics pages should sound like bioinformatics people talk — jargon-heavy but explained, not dumbed down. Clinical pages should sound like clinicians, not data scientists.
- **Include evaluative commentary**: "This is a bad idea", "We recommend against this approach", "This works in practice, though the purists hate it"
- **Break genre expectations occasionally**: Not every section needs the same rhetorical move order. Mix explanation → example → opinion → data.

### DON'T
- **Write metadiscourse that merely describes what the text does**: "This section discusses the importance of..." — humans don't narrate their own structure like this
- **Be consistently neutral**: AI text hedges everything equally. Humans take strong positions on some things and hedged positions on others — vary the confidence level.
- **Use the same stance pattern repeatedly**: If you say "Importantly," at the start of every paragraph, that's a tell. Mix stance markers: some at the start, some mid-sentence, some implied through word choice.
- **Copy academic register into blog posts**: A bioinformatics tutorial and a clinical diagnostics page should NOT sound like the same person wrote them. Different audiences = different tone.

### Register Awareness
| Page type | Expected register | Common AI tell |
|-----------|------------------|----------------|
| Tool page (primer, BLAST) | Technical but practical, first-person plural | Neutral hedging, no opinions |
| Blog post | Conversational, opinionated, varied | Same academic tone as tool pages |
| Glossary | Definitional but with examples | Circular definitions, no practical context |
| Landing page | Persuasive but grounded | Overclaiming, "powerful" / "robust" language |
| Developer docs | Precise, specific, no fluff | Verbose descriptions, round numbers in examples |

---

## 1C. EPISTEMIC/CONTENT CUES — Do You Actually Know This?

This cue family matters where **truthfulness, grounding, and authenticity** are evaluated. AI text can sound authoritative while saying nothing verifiable. The fix: ground claims in specifics, cite real things, and acknowledge what you don't know.

### DO
- **Cite specific papers, datasets, or protocols**: "SantaLucia (1998) nearest-neighbor model" not "the nearest-neighbor thermodynamic model"
- **Include worked examples with real sequences**: Show a real primer pair, a real BLAST result, a real docking score — not placeholder text
- **State limitations honestly**: "This tool doesn't handle modified bases yet", "We haven't validated this against plant genomes"
- **Reference your own data**: "When we ran 500 primer pairs through the calculator, we found..." — this grounds the text in experience
- **Use specific numbers from real use cases**: "GAPDH primers (NM_002046) give Tm = 58.3°C" not "typical primer pairs yield melting temperatures in the expected range"

### DON'T
- **Make claims you can't back up**: "Our tool is the most accurate available" — you can't prove this without a benchmark study
- **Use vague grounding**: "Extensive research has shown..." — which research? When? Who?
- **Fabricate statistics**: Don't invent "95% accuracy" or "10,000+ users" without real data behind it
- **Hallucinate biological facts**: Every gene name, accession number, protein ID, and sequence MUST be verified. A fake accession number is a massive credibility hit.
- **Sound authoritative about things you haven't tested**: If you haven't benchmarked against Primer3, don't claim you're better than Primer3

### Content Authenticity Checklist
- [ ] Every gene/protein reference has a real accession number (verified against NCBI/UniProt)
- [ ] Every sequence shown is biologically plausible (real ORF, correct reading frame)
- [ ] Every citation is real and findable (DOI or PubMed ID exists)
- [ ] Every number comes from actual tool output or published data, not invented
- [ ] No "extensive research" or "growing body of evidence" without specific references

---

## 1D. PREDICTABILITY/PROBABILISTIC CUES — The Detector Signal

> ⛔ **RETIRED (2026-10-02) — DO NOT FOLLOW.** Superseded by Human-First Part 1 rule #4 ("Never try to beat AI detectors") and rule #3 (never fake human involvement). Original text is kept below for history only; it must not be used as guidance or as an approval criterion.


This is what automated AI detectors actually measure. You can't fully control this (detectors use perplexity, entropy, token probability ranks), but you can reduce the signal they exploit.

### What Detectors Measure
1. **Perplexity** — How predictable each token is given the context. AI text has low perplexity (each word is statistically likely).
2. **Burstiness** — Sentence length variance. AI text has low burstiness (similar-length sentences throughout).
3. **Token probability ranks** — AI models assign high probability to common tokens. GLTR and DetectGPT exploit this.
4. **Vocabulary diversity** — AI text repeats certain function words and transitions at higher rates than humans.

### How to Reduce the Signal
- **Use uncommon word choices**: "We ran a paired-samples t-test" → "We ran a paired t-test on the pre/post scores" (varied structure, less predictable token sequence)
- **Include rare domain terms**: "Taq polymerase", "Sanger sequencing", "NEB Buffer 2.1" — specific terms have lower probability than generic ones
- **Break predictable sentence patterns**: Don't always start with the subject. "Got p = 0.03. Not convincing." (Fragment → fragment → longer sentence)
- **Include numerical details**: Specific numbers (e.g., "Tm = 58.3°C", "n = 127") have lower perplexity in context than vague quantifiers ("approximately", "several")
- **Use dashes, parentheses, and em-dashes**: These disrupt the clean token sequences that detectors expect

### DON'T
- **Write in perfectly predictable token sequences**: "The results demonstrate that the proposed method achieves significant improvements" — every token here is statistically likely given the context.
- **Use the same sentence opener 3+ times in a row**: Detectors flag repetitive positional patterns.
- **Keep all sentences within 15-25 words**: That's the AI sweet spot. Mix in 5-word sentences and 40-word sentences.

---

## 1E. STABILITY UNDER REVISION — Paraphrasing Destroys Cues

> ⛔ **RETIRED (2026-10-02) — DO NOT FOLLOW.** Superseded by Human-First Part 1 rule #4 ("Never try to beat AI detectors") and rule #3 (never fake human involvement). Original text is kept below for history only; it must not be used as guidance or as an approval criterion.


Research shows that **paraphrasing and post-editing are the #1 destabilizer** of AI detection signals. This means:

### Implications for Our Content
1. **If a human edits AI-drafted text, the detection signal weakens** — but surface and discourse cues can persist if the edit is light
2. **Our content goes through human review** — this is good. It means the original AI generation signal is partially erased.
3. **But light edits don't fully mask the AI origin** — stance, metadiscourse, and epistemic markers can still leak through

### What This Means in Practice
- Don't just run AI output through a paraphraser and publish. The probabilistic signal weakens but surface/discourse cues remain.
- **Genuinely rewrite sections** — change the rhetorical structure, not just the vocabulary. Move the opinion to a different position. Change which information comes first.
- **Add first-hand experience** — "When we tested this with SARS-CoV-2 N1 primers..." can't be generated by an LLM. It's grounded in your actual work.
- **Vary structure across similar pages** — If two landing pages cover similar topics, they should NOT follow the same paragraph structure. AI templates produce similar structure; humans vary it.

---

## 2. PAGE LAYOUT & MARGINS

### Content Width
- **Blog posts:** max-width 680-720px for body text, BUT the full page should use the full container (1100px). Sidebars, related articles, and author info should fill the extra space.
- **Landing pages:** max-width 800-900px for body content. Hero sections should be full-width.
- **NEVER center a narrow column on a wide page with empty whitespace on both sides.** This is the #1 AI visual tell.

### Margins & Spacing
- Section padding: 48-64px vertical (not 80-100px)
- Between sections: 32-48px (not 64-80px)
- The "hero" section should NOT have massive padding. Keep it tight: 48px top, 24px bottom.
- Content sections should feel connected, not isolated islands of text.

### What NOT to do
- Don't put a giant "Table of Contents" box at the top of every page. AI pages do this. Instead:
  - For blog posts: Make the TOC a small, unobtrusive sidebar or skip it entirely
  - For landing pages: No TOC needed
- Don't center every heading. Left-align most content.
- Don't use identical blue gradient CTA boxes everywhere. Vary the style.

---

## 3. VISUAL ELEMENTS — Break the Pattern

### Tables
- Don't make every table identical (same header bg, same cell padding)
- Some tables should have no borders, some should have minimal lines
- Occasionally put a table inside a colored box, sometimes leave it plain
- Use `<th>` with left-align, not always center-align with uppercase

### Callouts / Info Boxes
- Don't use blue callout boxes everywhere. Vary:
  - Simple bold text: "Note: this only applies to small samples."
  - Indented blockquote: `>` style
  - Colored background on a single paragraph
  - Sidebar aside boxes (floating right, 300px wide)
  - Yellow/amber warning boxes instead of always blue info boxes
- Limit: max 2-3 callout boxes per article. Not one per section.

### Bullet Lists
- Don't have a bullet list in every section. Mix with:
  - Inline commas: "Check normality, independence, and homogeneity of variance."
  - Numbered steps when the order matters
  - Bold key terms followed by colon description
  - Narrative paragraphs that describe the same information without bullets

### Headings
- Not every H2 needs to be a question or a "How to..." pattern
- Mix: "The ANOVA Problem", "Why Your p-Value Is Lying", "Effect Size: The Metric Nobody Reports"
- Some sections can start with a brief anecdote before the heading

### Images / Visual Breaks
- Add at least one visual break per 500 words of content
- Could be: a diagram, a screenshot, a callout box with a different color, a pull quote, a small table
- Pure text pages with no visual breaks scream "AI-generated"

---

## 4. CONTENT STRUCTURE

### Don't Follow This Pattern
Every section = H2 → 2 paragraphs → bullet list → blue callout box. This is the #1 AI template.

### Do This Instead
- Some sections start with a short anecdote or example
- Some sections are just a table with one sentence of context
- Some sections are a worked example with no bullets at all
- Some sections mix paragraphs and lists inline
- The CTA should appear at natural breaks, not always at the end
- Related content links should be contextual, not a generic "Related Articles" grid

### Paragraph Structure
- First paragraph of a section can be a single sentence
- Later paragraphs can be longer (4-5 sentences)
- Alternate between short and long paragraphs
- Start at least one paragraph with a question

---

## 5. CODE & HTML

### Semantic HTML
- Use `<article>`, `<section>`, `<aside>`, `<figure>`, `<figcaption>` where appropriate
- Don't use `<div>` soup — every meaningful element should have a semantic tag
- Use `<aside>` for sidebar content, not a div with a class

### Metadata
- Every page MUST have: og:title, og:description, og:image, og:type, canonical, twitter:card
- Every page MUST have: `<meta name="author">` (use a real team name, not "VigyanLLM Private Limited")
- Use `<meta property="article:published_time">` for blog posts
- Favicons and apple-touch-icon must be present

### Inline Styles
- Minimize inline `style=""` attributes on tables. Move table styling to CSS classes.
- AI pages are full of `style="padding:12px;border:1px solid #E2E8F0"` on every `<td>`

### CSS
- Don't redefine CSS variables that already exist in design-tokens.css
- Don't duplicate the same CSS across multiple pages — use shared stylesheets
- Keep CSS organized: variables → reset → layout → components → responsive

---

## 6. DEVELOPER PAGES SPECIFIC

- Don't copy-paste the same nav bar across 5 pages — use a shared component
- Don't copy-paste the same CSS across 5 pages — use a shared stylesheet
- Endpoint descriptions should be 2-3 sentences, not 1 sentence
- JSON examples should use realistic values, not round numbers
- Placeholder sequences should be real biological sequences (not ATGCGATCGATCG...)
- Empty states should be specific: "No API keys yet — generate one to test the primer design endpoint" not "No API keys yet"

---

## 7. CHECKLIST BEFORE DEPLOYING ANY PAGE

Run through this list before pushing any new page:

### Surface Cues (Writing Style)
- [ ] Does the content use contractions? (at least 5 per 500 words)
- [ ] Is there at least one instance of first-person ("we", "I")?
- [ ] Are sentences varied in length? (at least one under 10 words, at least one over 25 words)
- [ ] Are there "Furthermore" / "Moreover" / "In conclusion" anywhere? (delete them)
- [ ] Is every paragraph exactly 2-3 sentences? (break up at least one, extend at least one)
- [ ] Are there more than 3 blue callout boxes? (remove some, vary the style)

### Discourse/Pragmatic Cues (Rhetorical Posture)
- [ ] Does the author take a clear stance on at least one thing? (not everything hedged)
- [ ] Are metadiscourse markers varied? (not all at paragraph starts)
- [ ] Does the register match the page type? (tool page ≠ blog post ≠ glossary)
- [ ] Is there evaluative commentary? ("This is a bad idea", "We recommend against...")

### Epistemic/Content Cues (Grounding & Authenticity)
- [ ] Are gene/protein references verified against NCBI/UniProt?
- [ ] Are all accession numbers real and findable?
- [ ] Are citations real (DOI or PubMed ID exists)?
- [ ] Are statistics from actual tool output or published data?
- [ ] Does the text acknowledge limitations honestly?

### Specificity & Evidence (was "Probabilistic Cues"; detector-evasion items removed per Part 1 rule #4)
- [ ] Are numerical details included (specific Tm values, sample sizes, accession numbers)?
- [ ] Are claims backed by real sources (DOIs, tool versions, actual runs)?
- [ ] Has a qualified human reviewed the substance? (Part 1 rule #2)

### Layout & Visual
- [ ] Is the content max-width > 800px? (widen it or add sidebar content)
- [ ] Is there a giant TOC box at the top? (remove or shrink it)
- [ ] Do all tables have identical styling? (vary at least one)
- [ ] Are there bullet lists in every section? (convert some to inline prose)
- [ ] Is there at least one visual break per 500 words?
- [ ] Does the page have og:image, canonical, twitter:card?
- [ ] Is the byline truthful — a real named person only if they actually own/reviewed the page, otherwise the organization? (Part 1 rules #1, #3)
- [ ] Is inline style used on table cells? (move to CSS class)
- [ ] Does the page look like every other page on the site? (add unique elements)

### Review & Revision (was "Stability Under Revision")
- [ ] Has AI-drafted text been substantively reviewed by a qualified human before publication? (Part 1 rules #2, #5)
- [ ] Is any first-hand experience mentioned genuinely real — never invented? (Part 1 rule #3)
- [ ] Do similar pages on the site have different paragraph structures?

---

## 8. ANTI-AI DETECTION — Technical Details

> ⛔ **RETIRED (2026-10-02) — DO NOT FOLLOW.** Superseded by Human-First Part 1 rule #4 ("Never try to beat AI detectors") and rule #3 (never fake human involvement). Original text is kept below for history only; it must not be used as guidance or as an approval criterion.


These are the markers that AI detectors look for:

### Textual Markers
1. **Low perplexity** — AI text is statistically predictable. Add unexpected word choices.
2. **Low burstiness** — Sentence length variance. Humans naturally mix short and long.
3. **Overused transitions** — "Furthermore", "Moreover", "In conclusion", "It is important to note", "Delve into"
4. **Hallucinated depth** — AI sounds authoritative while saying nothing specific. Add real numbers, real examples.
5. **Perfect grammar throughout** — Humans make minor style choices (fragments, dashes, parentheticals).

### Code/HTML Markers
6. **Overly nested HTML** — `<div>` soup with 5+ levels of nesting
7. **Boilerplate metadata** — Default OG tags, missing canonical, generic descriptions
8. **Identical repeated structures** — Same card layout, same callout, same table format
9. **No unique CSS** — Every page copies the same styles instead of sharing
10. **Clean JSON examples** — Round numbers, perfect formatting, no edge cases

### Visual Markers
11. **Symmetric layouts** — Everything centered, everything balanced
12. **Identical spacing** — Same padding/margins everywhere
13. **No visual noise** — No handwritten notes, no slight imperfections, no unique styling
14. **Generic images** — Stock photos, placeholder graphics
15. **Perfect alignment** — Nothing slightly off-center or overlapping

---

## 9. BIOINFORMATICS DOMAIN-SPECIFIC RULES

Bioinformatics text has genre-specific AI tells. These pages must sound like bench scientists and computational biologists, not like general-purpose writers who happen to mention biology.

### DO
- **Use real gene/protein names with accession numbers**: "Human GAPDH (NM_002046)" — never "a housekeeping gene"
- **Reference specific tools and versions**: "Primer3 v2.6.1", "BLAST+ 2.14.0", "AutoDock Vina 1.2.3" — not "popular bioinformatics tools"
- **Include command-line or parameter details**: "Na+ = 50 mM, Mg2+ = 1.5 mM, dNTPs = 0.2 mM" — this grounds the text in real usage
- **Mention edge cases from actual runs**: "When the input sequence has a poly-T stretch longer than 8 bases, the Tm calculation can drift by 2-3°C"
- **Use biological shorthand naturally**: "ORF", "CDS", "UTR", "SNP", "Indel" — bioinformaticians use these without expanding them every time
- **Reference databases with version numbers**: "NCBI RefSeq release 225", "UniProt 2024_04"

### DON'T
- **Use generic biology language**: "DNA, the building block of life" — our audience knows this
- **Describe tools as "powerful" or "cutting-edge"**: Bioinformaticians judge tools by accuracy and speed, not adjectives
- **Use placeholder sequences**: `ATCGATCGATCG...` — use real sequences from real genes
- **Claim accuracy without benchmarks**: "Our primer design tool achieves 99% accuracy" — accuracy against what? Which dataset?
- **Ignore version dependencies**: Bioinformatics tools are version-sensitive. Always specify.
- **Write like a textbook**: Our pages are tools and tutorials, not encyclopedias. Practical > comprehensive.

### Bioinformatics-Specific AI Tells to Avoid
| Pattern | Why it's an AI tell | What to do instead |
|---------|--------------------|--------------------|
| "PCR is a fundamental technique in molecular biology" | Everyone knows this; humans skip it | Start with the actual protocol or problem |
| "The Primer-BLAST algorithm is widely used" | Vague, no specifics | "Primer-BLAST (Ye et al. 2012) uses Primer3 to generate candidates, then BLASTs them against nr" |
| "This tool provides comprehensive analysis" | "Comprehensive" is a top AI marker | "This tool calculates Tm, GC%, hairpin ΔG, and self-dimer ΔG" (list what it actually does) |
| "In the rapidly evolving field of genomics" | Top AI cliché for scientific writing | Start with the specific problem you're solving |
| "Understanding X is crucial for Y" | Filler that adds no information | "X matters for Y because [specific reason]" |

---

*Last updated: September 2026*
*Evidence basis: Georgiou, G.P. (2026). "What Distinguishes AI-Generated from Human Writing? A Rapid Review of the Literature." Big Data and Cognitive Computing, 10(55). doi:10.3390/bdcc10020055*
*This document is a living guide. Update it as we learn what works.*
