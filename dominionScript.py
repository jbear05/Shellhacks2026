import PyPDF2
import re

def extract_utility_projects(pdf_path):
    projects = []
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            
            if not text:
                continue
                
            # DEBUG: Print the raw text of the very first page so you can see the invisible characters
            if page_num == 0:
                print("--- RAW TEXT FROM PAGE 1 (DEBUG) ---")
                print(repr(text)) 
                print("------------------------------------\n")
                
            if "Project ID" in text:
                
                # 1. ID sits between "Project ID" and "Project Description"
                id_match = re.search(r"Project ID\s+(.*?)\s+Project Description", text, re.DOTALL | re.IGNORECASE)
                project_id = id_match.group(1).strip() if id_match else "Unknown"
                
                # 2. Date sits between "Planned In-Service Date" and "Estimated Project Cost"
                date_match = re.search(r"Planned In-Service Date\s+(.*?)\s+Estimated Project Cost", text, re.DOTALL | re.IGNORECASE)
                date = date_match.group(1).strip() if date_match else "Unknown"
                
                # 3. Title sits between "5 Year Budget" and "Project ID"
                title_match = re.search(r"5 Year Budget\s+(.*?)\s+Project ID", text, re.DOTALL | re.IGNORECASE)
                # Remove any random newlines that happen inside the title
                raw_title = title_match.group(1).strip().replace('\n', ' ') if title_match else "Unknown"
                
                projects.append({
                    "project_id": project_id,
                    "title": raw_title,
                    "in_service_date": date
                })

    return projects

extracted_data = extract_utility_projects("2024-2028-2million-and-above-project-descriptions.pdf")

for project in extracted_data:
    print(f"ID: {project['project_id']}")
    print(f"Title: {project['title']}")
    print(f"Date: {project['in_service_date']}")
    print("-" * 40)