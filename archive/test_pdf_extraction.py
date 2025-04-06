"""
Test script for PDF extraction functionality.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the project directory to the Python path to make imports work
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Import required modules
from src.canvas_mcp.utils.pdf_extractor import extract_text_from_pdf_url, extract_text_from_pdf
from src.canvas_mcp.canvas_client import CanvasClient

# Load environment variables
load_dotenv()
API_KEY = os.environ.get("CANVAS_ACCESS_TOKEN") or os.environ.get("CANVAS_API_KEY")
API_URL = os.environ.get("CANVAS_BASE_URL") or os.environ.get("CANVAS_API_URL")

# Database path
DB_PATH = project_dir / "data" / "canvas_mcp.db"

print("=== PDF Extraction Test ===")
print(f"Using API URL: {API_URL}")
print(f"Using database: {DB_PATH}")

# 1. Test the PDF extraction from a URL
print("\n1. Testing PDF extraction from a URL")
test_pdf_url = input("Enter a PDF URL to test, or press Enter to skip: ")
if test_pdf_url:
    print(f"Attempting to extract text from: {test_pdf_url}")
    text = extract_text_from_pdf_url(test_pdf_url)
    if text:
        print(f"Successfully extracted {len(text)} characters from the PDF")
        preview = text[:500] + "..." if len(text) > 500 else text
        print(f"Preview: {preview}")
    else:
        print("Failed to extract text from the URL")
else:
    print("Skipping URL test")

# 2. Create a Canvas client and get courses
print("\n2. Getting courses from Canvas")
try:
    client = CanvasClient(str(DB_PATH), API_KEY, API_URL)
    if not client.canvas:
        print("Failed to create Canvas client")
        sys.exit(1)
        
    # Get the user
    user = client.canvas.get_current_user()
    print(f"Authenticated as: {user.name} (ID: {user.id})")
    
    # Get courses
    conn, cursor = client.connect_db()
    cursor.execute("SELECT id, canvas_course_id, course_code, course_name FROM courses")
    courses = cursor.fetchall()
    conn.close()
    
    if not courses:
        print("No courses found in the database. Please run 'sync_courses' first.")
        sys.exit(1)
        
    print(f"Found {len(courses)} courses:")
    for i, course in enumerate(courses):
        print(f"{i+1}. {course['course_name']} ({course['course_code']}) - ID: {course['id']}")
        
    # Select a course
    selection = input(f"\nSelect a course (1-{len(courses)}): ")
    try:
        selected_index = int(selection) - 1
        selected_course = courses[selected_index]
    except (ValueError, IndexError):
        print("Invalid selection. Using the first course.")
        selected_course = courses[0]
        
    print(f"\nSelected course: {selected_course['course_name']} (ID: {selected_course['id']})")
    
    # 3. Find PDF files in the course
    print("\n3. Finding PDF files in the course")
    pdf_files = client.extract_pdf_files_from_course(selected_course['id'])
    
    if not pdf_files:
        print("No PDF files found in the course.")
        sys.exit(0)
        
    print(f"Found {len(pdf_files)} PDF files:")
    for i, pdf in enumerate(pdf_files):
        name = pdf.get('name', 'Unnamed PDF')
        url = pdf.get('url', 'No URL')
        source = pdf.get('source', 'Unknown source')
        print(f"{i+1}. {name}")
        print(f"   URL: {url}")
        print(f"   Source: {source}")
        
        # Additional info
        if 'module_name' in pdf:
            print(f"   Module: {pdf['module_name']}")
            
        if 'assignment_id' in pdf:
            print(f"   Assignment ID: {pdf['assignment_id']}")
        print()
        
    # 4. Extract text from a PDF
    print("\n4. Testing PDF text extraction")
    pdf_selection = input(f"Select a PDF to extract (1-{len(pdf_files)}), or Enter to skip: ")
    
    if pdf_selection:
        try:
            pdf_index = int(pdf_selection) - 1
            selected_pdf = pdf_files[pdf_index]
            
            pdf_url = selected_pdf.get('url')
            if not pdf_url:
                print("No URL available for this PDF.")
                sys.exit(0)
                
            print(f"Extracting text from: {selected_pdf.get('name', 'Unnamed PDF')}")
            print(f"URL: {pdf_url}")
            
            # Extract text
            text = extract_text_from_pdf(pdf_url)
            if text:
                print(f"\nSuccessfully extracted {len(text)} characters from the PDF.")
                print("\nText preview:")
                preview = text[:1000] + "..." if len(text) > 1000 else text
                print(preview)
                
                # Save to file option
                save_option = input("\nSave extracted text to file? (y/n): ")
                if save_option.lower() == 'y':
                    file_name = f"pdf_extract_{selected_course['id']}_{pdf_index+1}.txt"
                    with open(file_name, 'w', encoding='utf-8') as f:
                        f.write(text)
                    print(f"Text saved to {file_name}")
            else:
                print("Failed to extract text from the PDF.")
        except (ValueError, IndexError):
            print("Invalid selection.")
    else:
        print("Skipping text extraction.")
    
except Exception as e:
    print(f"Error: {e}")

print("\nPDF extraction test completed.")
