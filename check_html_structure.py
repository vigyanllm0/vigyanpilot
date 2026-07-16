import glob
import re

files = glob.glob("/Users/macbookpro/Desktop/vigyanpilot/frontend/**/*.html", recursive=True)

errors = []
for f in files:
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    # 1. Check if <nav> comes BEFORE <body>
    head_end = content.find("</head>")
    body_start = content.find("<body>")
    nav_start = content.find("<nav>")
    
    if head_end != -1 and nav_start != -1 and body_start != -1:
        if nav_start < body_start:
            errors.append(f"{f}: <nav> is before <body>")
            
    # 2. Check for missing </body> or </html>
    if "</body>" not in content:
        errors.append(f"{f}: Missing </body>")
    if "</html>" not in content:
        errors.append(f"{f}: Missing </html>")
        
    # 3. Check for multiple <nav> tags
    if content.count("<nav>") > 1:
        errors.append(f"{f}: Multiple <nav> tags")
        
    # 4. Check for orphaned tags
    body_count = content.count("<body>")
    body_end_count = content.count("</body>")
    if body_count != body_end_count:
        errors.append(f"{f}: Mismatched <body> ({body_count}) and </body> ({body_end_count}) tags")
        
    main_count = content.count("<main>")
    main_end_count = content.count("</main>")
    if main_count != main_end_count:
        errors.append(f"{f}: Mismatched <main> ({main_count}) and </main> ({main_end_count}) tags")

if errors:
    print("Found structural errors in HTML files:")
    for e in errors:
        print(e)
else:
    print("All HTML files passed basic structural checks.")

