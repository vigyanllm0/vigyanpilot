import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. except Exception:\n\s*pass
    # We want to replace it with:
    # except Exception as e:\n\s*logger.warning("Suppressed exception: %s", e)
    
    def repl1(m):
        spaces = m.group(1)
        return f'except Exception as e:\n{spaces}logger.debug("Suppressed exception: %s", e)'
        
    content, n1 = re.subn(r'except Exception:\n(\s*)pass', repl1, content)
    
    def repl2(m):
        spaces = m.group(1)
        return f'except Exception as e:\n{spaces}logger.debug("Suppressed bare except: %s", e)'
        
    content, n2 = re.subn(r'except:\n(\s*)pass', repl2, content)
    
    # also except Exception as e: logger.debug("Suppressed exception: %s", e) -> on same line
    content, n3 = re.subn(r'except \([^)]+\):\s*pass', r'except Exception as e: logger.debug("Suppressed exception: %s", e)', content)
    
    # bare except Exception as e: logger.debug("Suppressed exception: %s", e) on same line
    content, n4 = re.subn(r'except:\s*pass', r'except Exception as e: logger.debug("Suppressed exception: %s", e)', content)

    # except Exception as e: logger.debug("Suppressed exception: %s", e) on same line
    content, n5 = re.subn(r'except Exception:\s*pass', r'except Exception as e: logger.debug("Suppressed exception: %s", e)', content)
    
    total = n1 + n2 + n3 + n4 + n5
    if total > 0:
        # Check if logger is imported/defined
        if 'logger =' not in content and 'import logging' not in content:
            # simple fallback if no logger
            content = content.replace('logger.debug', 'print')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {total} occurrences in {filepath}")

def main():
    repo_dir = "/Users/macbookpro/Desktop/vigyanpilot"
    for root, dirs, files in os.walk(repo_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                fix_file(filepath)

if __name__ == "__main__":
    main()
