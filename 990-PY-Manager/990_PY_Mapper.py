# import streamlit as st
# import pandas as pd
# import io
# import zipfile
# from excel_processor import ExcelProcessor
# from file_utils import increment_year_in_filename, validate_excel_file

# st.set_page_config(
#     page_title="990 PY Mapper", 
#     layout="wide",
#     initial_sidebar_state="expanded",
#     page_icon="static\\HCLLP.ico"
# )

# def main():
#     st.title("990 PY Mapper")
#     st.markdown("### AI-powered financial data migration from prior year workbooks to current year templates")
    
#     st.markdown("---")
    
#     # Instructions
#     with st.expander("📋 Instructions", expanded=True):
#         st.markdown("""
#         **How to use this tool:**
#         1. Upload your **prior year Excel workbooks** (input files)
#         2. Upload **one blank Excel template** (will be used for all input files)
#         3. The tool will process each file using **row 3 as headers** and apply the following mappings:
        
#         **SOR Sheet:** Particulars → Particulars, Amount (CY) → Amount (LY), 990 Mapping (CY) → 990 Mapping (LY)
        
#         **SOFE Sheet:** Particulars → Particulars, Total (CY) → Total (LY), 990 Mapping (CY) → 990 Mapping (LY)
        
#         **SOFP Sheet:** Particulars → Particulars, 2nd column → 1st column after Particulars, 990 Mapping (CY) → 990 Mapping (LY)
        
#         4. Download all processed files as a single ZIP file
#         """)
    
#     # File upload sections
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.subheader("📁 Prior Year Workbooks (Input)")
#         input_files = st.file_uploader(
#             "Upload prior year Excel files",
#             type=['xlsx', 'xls'],
#             accept_multiple_files=True,
#             key="input_files",
#             help="Select one or more Excel workbooks from the prior year"
#         )
    
#     with col2:
#         st.subheader("📄 Blank Template (Output)")
#         template_file = st.file_uploader(
#             "Upload one blank Excel template",
#             type=['xlsx', 'xls'],
#             accept_multiple_files=False,
#             key="template_file",
#             help="Select one blank Excel template that will be used for all input files"
#         )
    
#     # Validation and processing
#     if input_files and template_file:
#         st.success(f"✅ Ready to process {len(input_files)} file(s) using the template: {template_file.name}")
        
#         # File processing information
#         with st.expander("📋 Processing Preview"):
#             st.write(f"**Template:** `{template_file.name}`")
#             st.write(f"**Input files to process:**")
#             for i, input_file in enumerate(input_files):
#                 st.write(f"  {i+1}. `{input_file.name}`")
        
#         # Process button
#         if st.button("🚀 Process Files", type="primary", use_container_width=True):
#             process_files(input_files, template_file)

# def process_files(input_files, template_file):
#     """Process all input files using the single template and provide ZIP download"""
    
#     processor = ExcelProcessor()
#     progress_bar = st.progress(0)
#     status_text = st.empty()
    
#     processed_files = []
#     total_files = len(input_files)
    
#     # Validate template file first
#     if not validate_excel_file(template_file):
#         st.error(f"❌ Invalid template file: {template_file.name}")
#         return
    
#     for i, input_file in enumerate(input_files):
#         try:
#             # Update progress
#             progress = (i + 1) / total_files
#             progress_bar.progress(progress)
#             status_text.text(f"Processing {input_file.name}... ({i+1}/{total_files})")
            
#             # Validate input file
#             if not validate_excel_file(input_file):
#                 st.error(f"❌ Invalid input file: {input_file.name}")
#                 continue
            
#             # Process the file pair
#             output_buffer = processor.process_file_pair(input_file, template_file)
            
#             if output_buffer:
#                 # Generate output filename with incremented year
#                 output_filename = increment_year_in_filename(input_file.name)
                
#                 processed_files.append({
#                     'name': output_filename,
#                     'buffer': output_buffer,
#                     'original_input': input_file.name,
#                     'template_used': template_file.name
#                 })
                
#                 st.success(f"✅ Successfully processed: {input_file.name}")
#             else:
#                 st.error(f"❌ Failed to process: {input_file.name}")
                
#         except Exception as e:
#             st.error(f"❌ Error processing {input_file.name}: {str(e)}")
#             continue
    
#     # Complete progress
#     progress_bar.progress(1.0)
#     status_text.text("✅ Processing complete!")
    
#     # Display results and download ZIP
#     if processed_files:
#         st.markdown("---")
#         st.subheader("📥 Download All Processed Files")
        
#         # Create ZIP file with all processed files
#         zip_buffer = io.BytesIO()
#         with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#             for file_info in processed_files:
#                 zip_file.writestr(file_info['name'], file_info['buffer'].getvalue())
        
#         zip_buffer.seek(0)
        
#         # Display file list
#         with st.expander("📋 Files in ZIP Package", expanded=True):
#             for file_info in processed_files:
#                 st.write(f"✅ **{file_info['name']}**")
#                 st.caption(f"Source: {file_info['original_input']} | Template: {file_info['template_used']}")
        
#         # Single download button for ZIP
#         from datetime import datetime
#         current_date = datetime.now().strftime("%Y%m%d")
#         zip_filename = f"Processed_Excel_Files_{current_date}.zip"
        
#         st.download_button(
#             label="📦 Download All Files as ZIP",
#             data=zip_buffer.getvalue(),
#             file_name=zip_filename,
#             mime="application/zip",
#             type="primary",
#             use_container_width=True
#         )
        
#         st.success(f"🎉 Successfully processed {len(processed_files)} out of {total_files} file(s)")
#     else:
#         st.error("❌ No files were successfully processed. Please check your input files and try again.")

# if __name__ == "__main__":
#     main()

































# import streamlit as st
# import pandas as pd
# import io
# import zipfile
# import requests
# import base64
# from PIL import Image
# from io import BytesIO
# from excel_processor import ExcelProcessor
# from file_utils import increment_year_in_filename, validate_excel_file
# from datetime import datetime

# st.set_page_config(
#     page_title="990 PY Mapper", 
#     layout="wide",
#     initial_sidebar_state="collapsed",
#     page_icon="static/HCLLP.ico"
# )

# # Custom CSS for styling
# def load_custom_css():
#     st.markdown("""
#     <style>
#     /* Hide Streamlit defaults */
#     #MainMenu, footer, header {visibility: hidden;}
    
#     /* Global styles */
#     .main {
#         background: #f8f9fa !important;
#         padding: 0 !important;
#     }
    
#     .block-container {
#         padding: 1rem 2rem 2rem 2rem !important;
#         max-width: 100% !important;
#     }
    
#     /* Header styling - Fixed at top */
#     .header-container {
#         background: white;
#         padding: 1.5rem 2rem;
#         border-bottom: 1px solid #e5e7eb;
#         box-shadow: 0 2px 8px rgba(0,0,0,0.1);
#         display: flex;
#         justify-content: space-between;
#         align-items: center;
#         position: fixed;
#         top: 0;
#         left: 0;
#         right: 0;
#         width: 100%;
#         z-index: 1000;
#         backdrop-filter: blur(10px);
#         -webkit-backdrop-filter: blur(10px);
#     }
    
#     /* Add top padding to body content to account for fixed header */
#     .content-spacer {
#         height: 100px;
#         margin-bottom: 2rem;
#     }
    
#     .header-logo {
#         display: flex;
#         align-items: center;
#         height: 60px;
#     }
    
#     .header-logo img {
#         max-height: 60px;
#         max-width: 200px;
#         object-fit: contain;
#         transition: transform 0.3s ease;
#     }
    
#     .header-logo img:hover {
#         transform: scale(1.05);
#     }
    
#     .header-logo--right {
#         justify-content: flex-end;
#     }
    
#     .header-center {
#         position: absolute;
#         left: 50%;
#         transform: translateX(-50%);
#         text-align: center;
#     }
    
#     .greeting {
#         font-size: 1.75rem;
#         font-weight: 700;
#         color: #1f2937;
#         margin: 0;
#     }
    
#     .subtitle {
#         font-size: 1rem;
#         color: #6b7280;
#         margin: 0;
#     }
    
#     /* Metric cards using Streamlit's native styling */
#     .metric-row {
#         display: grid;
#         grid-template-columns: repeat(4, 1fr);
#         gap: 1.5rem;
#         margin: 2rem 0;
#     }
    
#     /* Override Streamlit's metric styling */
#     [data-testid="metric-container"] {
#         background: white;
#         border: 1px solid #e5e7eb;
#         padding: 1.5rem;
#         border-radius: 16px;
#         box-shadow: 0 1px 3px rgba(0,0,0,0.08);
#         transition: all 0.3s ease;
#     }
    
#     [data-testid="metric-container"]:hover {
#         transform: translateY(-2px);
#         box-shadow: 0 4px 12px rgba(0,0,0,0.12);
#         border-color: #d1d5db;
#     }
    
#     [data-testid="metric-container"] [data-testid="metric-value"] {
#         font-size: 2.25rem !important;
#         font-weight: 700 !important;
#         color: #1f2937 !important;
#     }
    
#     [data-testid="metric-container"] [data-testid="metric-label"] {
#         font-size: 0.875rem !important;
#         font-weight: 600 !important;
#         color: #374151 !important;
#         text-transform: uppercase;
#         letter-spacing: 0.05em;
#     }
    
#     [data-testid="metric-container"] [data-testid="metric-delta"] {
#         font-size: 0.8125rem !important;
#         color: #10b981 !important;
#     }
    
#     /* Section cards */
#     .section-card {
#         background: white;
#         border-radius: 16px;
#         padding: 1.75rem;
#         box-shadow: 0 1px 3px rgba(0,0,0,0.08);
#         border: 1px solid #e5e7eb;
#         margin: 1rem 0;
#     }
    
#     .section-title {
#         font-size: 1.25rem;
#         font-weight: 700;
#         color: #1f2937;
#         margin: 0 0 1.5rem 0;
#     }
    
#     /* Upload areas */
#     .upload-container {
#         border: 2px dashed #d1d5db;
#         border-radius: 12px;
#         padding: 1.5rem;
#         text-align: center;
#         background: #fafafa;
#         transition: all 0.3s ease;
#         margin-bottom: 1rem;
#     }
    
#     .upload-container:hover {
#         border-color: #8b5cf6;
#         background: #faf5ff;
#     }
    
#     .upload-title {
#         font-size: 1rem;
#         font-weight: 600;
#         color: #374151;
#         margin-bottom: 0.5rem;
#     }
    
#     .upload-desc {
#         font-size: 0.875rem;
#         color: #6b7280;
#     }
    
#     /* Buttons */
#     .stButton > button {
#         background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
#         color: white !important;
#         border: none !important;
#         border-radius: 12px !important;
#         padding: 0.875rem 1.75rem !important;
#         font-size: 0.9375rem !important;
#         font-weight: 600 !important;
#         transition: all 0.3s ease !important;
#         box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3) !important;
#         width: 100% !important;
#     }
    
#     .stButton > button:hover {
#         transform: translateY(-1px) !important;
#         box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4) !important;
#     }
    
#     .stDownloadButton > button {
#         background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
#         color: white !important;
#         border: none !important;
#         border-radius: 12px !important;
#         padding: 0.875rem 1.75rem !important;
#         font-size: 0.9375rem !important;
#         font-weight: 600 !important;
#         transition: all 0.3s ease !important;
#         box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
#         width: 100% !important;
#     }
    
#     .stDownloadButton > button:hover {
#         transform: translateY(-1px) !important;
#         box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4) !important;
#     }
    
#     /* File uploader styling */
#     .stFileUploader > div {
#         background: transparent !important;
#         border: none !important;
#     }
    
#     /* Progress bar */
#     .stProgress > div > div {
#         background: linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%) !important;
#         border-radius: 8px !important;
#         height: 8px !important;
#     }
    
#     /* Alert styling */
#     .stSuccess {
#         background: #f0fdf4 !important;
#         border-left: 4px solid #10b981 !important;
#         border-radius: 12px !important;
#         padding: 1rem !important;
#     }
    
#     .stError {
#         background: #fef2f2 !important;
#         border-left: 4px solid #ef4444 !important;
#         border-radius: 12px !important;
#         padding: 1rem !important;
#     }
    
#     /* Expander styling */
#     .streamlit-expanderHeader {
#         background: #f9fafb !important;
#         border-radius: 10px !important;
#         border: 1px solid #e5e7eb !important;
#         padding: 0.875rem 1.125rem !important;
#         font-weight: 600 !important;
#     }
    
#     .streamlit-expanderHeader:hover {
#         background: #f3f4f6 !important;
#         border-color: #d1d5db !important;
#     }
    
#     @media (max-width: 768px) {
#         .metric-row {
#             grid-template-columns: repeat(2, 1fr);
#         }
        
#         .app-header {
#             flex-direction: column;
#             gap: 1rem;
#             text-align: center;
#         }
#     }
    
#     @media (max-width: 480px) {
#         .metric-row {
#             grid-template-columns: 1fr;
#         }
#     }
#     </style>
#     """, unsafe_allow_html=True)

# def render_header():
#     """Render full-width header with brand logos"""
#     try:
#         # Left logo URL (Brand logo)
#         left_logo_url = "https://nativesecurity.us/image/Logo%202%203%2012.png"
#         left_response = requests.get(left_logo_url, timeout=10)
#         left_response.raise_for_status()
#         left_image = Image.open(BytesIO(left_response.content))
        
#         left_buffered = BytesIO()
#         left_image.save(left_buffered, format="PNG")
#         left_img_str = base64.b64encode(left_buffered.getvalue()).decode()
        
#         # Right logo URL (Tool logo)
#         right_logo_url = "https://nativesecurity.us/image/ChatGPT%20Image%20Oct%2010%2C%202025%2C%2005_21_13%20PM.png"
#         right_response = requests.get(right_logo_url, timeout=10)
#         right_response.raise_for_status()
#         right_image = Image.open(BytesIO(right_response.content))
        
#         right_buffered = BytesIO()
#         right_image.save(right_buffered, format="PNG")
#         right_img_str = base64.b64encode(right_buffered.getvalue()).decode()
        
#         # Render header with logos only (no text)
#         st.markdown(
#             f"""
#             <div class="header-container">
#                 <div class="header-logo">
#                     <img src="data:image/png;base64,{left_img_str}" alt="Brand Logo">
#                 </div>
#                 <div class="header-logo header-logo--right">
#                     <img src="data:image/png;base64,{right_img_str}" alt="Tool Logo">
#                 </div>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )
#     except Exception as e:
#         # Fallback header if logos fail to load
#         st.markdown("""
#         <div class="header-container">
#             <div class="header-logo">
#                 <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); color: white; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.5rem;">V</div>
#             </div>
#             <div class="header-logo header-logo--right">
#                 <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.5rem;">T</div>
#             </div>
#         </div>
#         """, unsafe_allow_html=True)
#         st.warning(f"Could not load logos: {str(e)}")

# def main():
#     # Load custom CSS
#     load_custom_css()
    
#     # Render fixed header with logos
#     render_header()
    
#     # Add spacer for fixed header
#     st.markdown('<div class="content-spacer"></div>', unsafe_allow_html=True)
    
#     # Initialize session state for stats
#     if 'stats' not in st.session_state:
#         st.session_state.stats = {
#             'total_files': 0,
#             'processed': 0,
#             'templates': 0,
#             'success_rate': 0
#         }
    
#     # KPI Metrics using Streamlit's native metric component
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         st.metric(
#             label="Total Files",
#             value=st.session_state.stats['total_files'],
#             delta="Ready to process"
#         )
    
#     with col2:
#         st.metric(
#             label="Processed",
#             value=st.session_state.stats['processed'],
#             delta="Successfully completed"
#         )
    
#     with col3:
#         st.metric(
#             label="Templates",
#             value=st.session_state.stats['templates'],
#             delta="Active templates"
#         )
    
#     with col4:
#         st.metric(
#             label="Success Rate",
#             value=f"{st.session_state.stats['success_rate']}%",
#             delta="Performance metric"
#         )
    
#     # Instructions
#     with st.expander("📋 How to Use This Tool", expanded=False):
#         st.markdown("""
#         **Step-by-step guide:**
        
#         1. **Upload Prior Year Workbooks** - Select one or more Excel files containing prior year data
#         2. **Upload Blank Template** - Choose a single blank Excel template for the current year
#         3. **Processing Details:**
#            - Headers are read from row 3 in all sheets
#            - Three sheets are processed: SOR, SOFE, and SOFP
        
#         **Column Mappings:**
        
#         - **SOR Sheet:** Particulars → Particulars | Amount (CY) → Amount (LY) | 990 Mapping (CY) → 990 Mapping (LY)
#         - **SOFE Sheet:** Particulars → Particulars | Total (CY) → Total (LY) | 990 Mapping (CY) → 990 Mapping (LY)
#         - **SOFP Sheet:** Particulars → Particulars | 2nd column → 1st column after Particulars | 990 Mapping (CY) → 990 Mapping (LY)
        
#         4. **Download** - Get all processed files in a single ZIP archive
#         """)
    
#     # File Upload Section
#     st.markdown('<div class="section-card">', unsafe_allow_html=True)
#     st.markdown('<h2 class="section-title">📂 File Upload</h2>', unsafe_allow_html=True)
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown("""
#         <div class="upload-container">
#             <div class="upload-title">📁 Prior Year Workbooks</div>
#             <div class="upload-desc">Upload one or more Excel files</div>
#         </div>
#         """, unsafe_allow_html=True)
        
#         input_files = st.file_uploader(
#             "Choose files",
#             type=['xlsx', 'xls'],
#             accept_multiple_files=True,
#             key="input_files",
#             help="Select one or more Excel workbooks from the prior year",
#             label_visibility="collapsed"
#         )
    
#     with col2:
#         st.markdown("""
#         <div class="upload-container">
#             <div class="upload-title">📄 Blank Template</div>
#             <div class="upload-desc">Upload a single template file</div>
#         </div>
#         """, unsafe_allow_html=True)
        
#         template_file = st.file_uploader(
#             "Choose template",
#             type=['xlsx', 'xls'],
#             accept_multiple_files=False,
#             key="template_file",
#             help="Select one blank Excel template that will be used for all input files",
#             label_visibility="collapsed"
#         )
    
#     st.markdown('</div>', unsafe_allow_html=True)
    
#     # Update stats
#     st.session_state.stats['total_files'] = len(input_files) if input_files else 0
#     st.session_state.stats['templates'] = 1 if template_file else 0
    
#     # Processing section
#     if input_files and template_file:
#         st.success(f"Ready to process {len(input_files)} file(s) using template: {template_file.name}")
        
#         # File processing information
#         with st.expander("📋 Processing Preview", expanded=False):
#             st.write(f"**Template:** `{template_file.name}`")
#             st.write(f"**Input files to process:**")
#             for i, input_file in enumerate(input_files):
#                 st.write(f"  {i+1}. `{input_file.name}`")
        
#         # Process button
#         if st.button("🚀 Process Files", type="primary"):
#             process_files(input_files, template_file)

# def process_files(input_files, template_file):
#     """Process all input files using the single template and provide ZIP download"""
    
#     processor = ExcelProcessor()
#     progress_bar = st.progress(0)
#     status_text = st.empty()
    
#     processed_files = []
#     total_files = len(input_files)
    
#     # Validate template file first
#     if not validate_excel_file(template_file):
#         st.error(f"Invalid template file: {template_file.name}")
#         return
    
#     for i, input_file in enumerate(input_files):
#         try:
#             # Update progress
#             progress = (i + 1) / total_files
#             progress_bar.progress(progress)
#             status_text.text(f"Processing {input_file.name}... ({i+1}/{total_files})")
            
#             # Validate input file
#             if not validate_excel_file(input_file):
#                 st.error(f"Invalid input file: {input_file.name}")
#                 continue
            
#             # Process the file pair
#             output_buffer = processor.process_file_pair(input_file, template_file)
            
#             if output_buffer:
#                 # Generate output filename with incremented year
#                 output_filename = increment_year_in_filename(input_file.name)
                
#                 processed_files.append({
#                     'name': output_filename,
#                     'buffer': output_buffer,
#                     'original_input': input_file.name,
#                     'template_used': template_file.name
#                 })
                
#                 st.success(f"Successfully processed: {input_file.name}")
#             else:
#                 st.error(f"Failed to process: {input_file.name}")
                
#         except Exception as e:
#             st.error(f"Error processing {input_file.name}: {str(e)}")
#             continue
    
#     # Complete progress
#     progress_bar.progress(1.0)
#     status_text.text("Processing complete!")
    
#     # Update stats
#     st.session_state.stats['processed'] = len(processed_files)
#     st.session_state.stats['success_rate'] = int((len(processed_files) / total_files) * 100) if total_files > 0 else 0
    
#     # Display results and download ZIP
#     if processed_files:
#         st.markdown('<div class="section-card">', unsafe_allow_html=True)
#         st.markdown('<h2 class="section-title">📥 Download Results</h2>', unsafe_allow_html=True)
        
#         # Create ZIP file with all processed files
#         zip_buffer = io.BytesIO()
#         with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#             for file_info in processed_files:
#                 zip_file.writestr(file_info['name'], file_info['buffer'].getvalue())
        
#         zip_buffer.seek(0)
        
#         # Display file list
#         with st.expander("📋 Files in ZIP Package", expanded=True):
#             for file_info in processed_files:
#                 st.write(f"**{file_info['name']}**")
#                 st.caption(f"Source: {file_info['original_input']} | Template: {file_info['template_used']}")
        
#         # Single download button for ZIP
#         current_date = datetime.now().strftime("%Y%m%d")
#         zip_filename = f"Processed_Excel_Files_{current_date}.zip"
        
#         st.download_button(
#             label="📦 Download All Files as ZIP",
#             data=zip_buffer.getvalue(),
#             file_name=zip_filename,
#             mime="application/zip",
#             type="primary"
#         )
        
#         st.success(f"Successfully processed {len(processed_files)} out of {total_files} file(s)")
#         st.markdown('</div>', unsafe_allow_html=True)
#     else:
#         st.error("No files were successfully processed. Please check your input files and try again.")

# if __name__ == "__main__":
#     main()

































import streamlit as st
import pandas as pd
import io
import zipfile
import requests
import base64
from PIL import Image
from io import BytesIO
from excel_processor import ExcelProcessor
from file_utils import increment_year_in_filename, validate_excel_file
from datetime import datetime
from config import config
from mongo_utils import get_db_manager

st.set_page_config(
    page_title="990 PY Mapper", 
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="static/HCLLP.ico"
)

# Custom CSS for styling (keeping your existing CSS)
def load_custom_css():
    st.markdown("""
    <style>
    /* Hide Streamlit defaults */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Global styles */
    .main {
        background: #f8f9fa !important;
        padding: 0 !important;
    }
    
    .block-container {
        padding: 1rem 2rem 2rem 2rem !important;
        max-width: 100% !important;
    }
    
    /* Header styling - Fixed at top */
    .header-container {
        background: white;
        padding: 1.5rem 2rem;
        border-bottom: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100%;
        z-index: 1000;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    
    /* Add top padding to body content to account for fixed header */
    .content-spacer {
        height: 100px;
        margin-bottom: 2rem;
    }
    
    .header-logo {
        display: flex;
        align-items: center;
        height: 60px;
    }
    
    .header-logo img {
        max-height: 60px;
        max-width: 200px;
        object-fit: contain;
        transition: transform 0.3s ease;
    }
    
    .header-logo img:hover {
        transform: scale(1.05);
    }
    
    .header-logo--right {
        justify-content: flex-end;
    }
    
    .header-center {
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        text-align: center;
    }
    
    .greeting {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1f2937;
        margin: 0;
    }
    
    .subtitle {
        font-size: 1rem;
        color: #6b7280;
        margin: 0;
    }
    
    /* Metric cards using Streamlit's native styling */
    .metric-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    /* Override Streamlit's metric styling */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-color: #d1d5db;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        font-size: 2.25rem !important;
        font-weight: 700 !important;
        color: #1f2937 !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-label"] {
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    [data-testid="metric-container"] [data-testid="metric-delta"] {
        font-size: 0.8125rem !important;
        color: #10b981 !important;
    }
    
    /* Section cards */
    .section-card {
        background: white;
        border-radius: 16px;
        padding: 1.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        margin: 1rem 0;
    }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1f2937;
        margin: 0 0 1.5rem 0;
    }
    
    /* Upload areas */
    .upload-container {
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        background: #fafafa;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .upload-container:hover {
        border-color: #8b5cf6;
        background: #faf5ff;
    }
    
    .upload-title {
        font-size: 1rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
    }
    
    .upload-desc {
        font-size: 0.875rem;
        color: #6b7280;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 1.75rem !important;
        font-size: 0.9375rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3) !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4) !important;
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 1.75rem !important;
        font-size: 0.9375rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
        width: 100% !important;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4) !important;
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        background: transparent !important;
        border: none !important;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%) !important;
        border-radius: 8px !important;
        height: 8px !important;
    }
    
    /* Alert styling */
    .stSuccess {
        background: #f0fdf4 !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    .stError {
        background: #fef2f2 !important;
        border-left: 4px solid #ef4444 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f9fafb !important;
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
        padding: 0.875rem 1.125rem !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f3f4f6 !important;
        border-color: #d1d5db !important;
    }
    
    /* Database status indicator */
    .db-status {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: white;
        padding: 8px 16px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        font-size: 0.8rem;
        z-index: 999;
    }
    
    .db-connected {
        color: #10b981;
        font-weight: 600;
    }
    
    .db-disconnected {
        color: #ef4444;
        font-weight: 600;
    }
    
    @media (max-width: 768px) {
        .metric-row {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .app-header {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
        }
    }
    
    @media (max-width: 480px) {
        .metric-row {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Render full-width header with brand logos"""
    try:
        left_logo_url = "https://nativesecurity.us/image/Logo%202%203%2012.png"
        left_response = requests.get(left_logo_url, timeout=10)
        left_response.raise_for_status()
        left_image = Image.open(BytesIO(left_response.content))
        
        left_buffered = BytesIO()
        left_image.save(left_buffered, format="PNG")
        left_img_str = base64.b64encode(left_buffered.getvalue()).decode()
        
        right_logo_url = "https://nativesecurity.us/image/ChatGPT%20Image%20Oct%2010%2C%202025%2C%2005_21_13%20PM.png"
        right_response = requests.get(right_logo_url, timeout=10)
        right_response.raise_for_status()
        right_image = Image.open(BytesIO(right_response.content))
        
        right_buffered = BytesIO()
        right_image.save(right_buffered, format="PNG")
        right_img_str = base64.b64encode(right_buffered.getvalue()).decode()
        
        st.markdown(
            f"""
            <div class="header-container">
                <div class="header-logo">
                    <img src="data:image/png;base64,{left_img_str}" alt="Brand Logo">
                </div>
                <div class="header-logo header-logo--right">
                    <img src="data:image/png;base64,{right_img_str}" alt="Tool Logo">
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.markdown("""
        <div class="header-container">
            <div class="header-logo">
                <div style="background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); color: white; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.5rem;">V</div>
            </div>
            <div class="header-logo header-logo--right">
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.5rem;">T</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def initialize_mongodb():
    """Initialize MongoDB connection and session tracking"""
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = get_db_manager()
        
        if config.MONGODB_ENABLED:
            connected = st.session_state.db_manager.connect(config.MONGODB_DB_NAME)
            st.session_state.db_connected = connected
            
            if connected:
                # Create or update session
                session_id = st.session_state.get('session_id', id(st.session_state))
                st.session_state.session_id = str(session_id)
                st.session_state.db_manager.create_or_update_session(
                    st.session_state.session_id,
                    {'user_agent': 'streamlit_app'}
                )
                st.session_state.db_manager.log_action(
                    'session_start',
                    {'timestamp': datetime.utcnow().isoformat()},
                    st.session_state.session_id
                )
        else:
            st.session_state.db_connected = False

# def render_db_status():
#     """Render database connection status indicator"""
#     if st.session_state.get('db_connected', False):
#         status_html = '<div class="db-status"><span class="db-connected">● MongoDB Connected</span></div>'
#     else:
#         status_html = '<div class="db-status"><span class="db-disconnected">○ MongoDB Offline</span></div>'
    
#     st.markdown(status_html, unsafe_allow_html=True)

def get_stats_from_db():
    """Get statistics from MongoDB or use session state"""
    if st.session_state.get('db_connected', False):
        db_manager = st.session_state.db_manager
        analytics = db_manager.get_analytics_summary(days=30)
        
        return {
            'total_files': analytics.get('total_files_processed', 0),
            'processed': analytics.get('completed_jobs', 0),
            'templates': st.session_state.stats.get('templates', 0),
            'success_rate': analytics.get('average_success_rate', 0)
        }
    else:
        return st.session_state.stats

# def render_history_section():
#     """Render processing history section"""
#     if not st.session_state.get('db_connected', False):
#         return
    
#     with st.expander("📊 Processing History", expanded=False):
#         db_manager = st.session_state.db_manager
#         recent_jobs = db_manager.get_recent_jobs(limit=10, session_id=st.session_state.session_id)
        
#         if recent_jobs:
#             history_data = []
#             for job in recent_jobs:
#                 history_data.append({
#                     'Date': job['created_at'].strftime('%Y-%m-%d %H:%M'),
#                     'Status': job['status'].title(),
#                     'Files': f"{job['processed_files']}/{job['total_files']}",
#                     'Success Rate': f"{job.get('success_rate', 0):.1f}%"
#                 })
            
#             df = pd.DataFrame(history_data)
#             st.dataframe(df, use_container_width=True, hide_index=True)
#         else:
#             st.info("No processing history available yet.")

def main():
    load_custom_css()
    render_header()
    
    # Initialize MongoDB
    initialize_mongodb()
    
    # Add spacer for fixed header
    st.markdown('<div class="content-spacer"></div>', unsafe_allow_html=True)
    
    # Initialize session state for stats
    if 'stats' not in st.session_state:
        st.session_state.stats = {
            'total_files': 0,
            'processed': 0,
            'templates': 0,
            'success_rate': 0
        }
    
    # Get statistics (from DB if available)
    stats = get_stats_from_db()
    
    # KPI Metrics using Streamlit's native metric component
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Files",
            value=stats['total_files'],
            delta="Ready to process"
        )
    
    with col2:
        st.metric(
            label="Processed",
            value=stats['processed'],
            delta="Successfully completed"
        )
    
    with col3:
        st.metric(
            label="Templates",
            value=stats['templates'],
            delta="Active templates"
        )
    
    with col4:
        st.metric(
            label="Success Rate",
            value=f"{stats['success_rate']:.1f}%",
            delta="Performance metric"
        )
    
    # # Processing History Section
    # render_history_section()
    
    # Instructions
    with st.expander("📋 How to Use This Tool", expanded=False):
        st.markdown("""
        **Step-by-step guide:**
        
        1. **Upload Prior Year Workbooks** - Select one or more Excel files containing prior year data
        2. **Upload Blank Template** - Choose a single blank Excel template for the current year
        3. **Processing Details:**
           - Headers are read from row 3 in all sheets
           - Three sheets are processed: SOR, SOFE, and SOFP
        
        **Column Mappings:**
        
        - **SOR Sheet:** Particulars → Particulars | Amount (CY) → Amount (LY) | 990 Mapping (CY) → 990 Mapping (LY)
        - **SOFE Sheet:** Particulars → Particulars | Total (CY) → Total (LY) | 990 Mapping (CY) → 990 Mapping (LY)
        - **SOFP Sheet:** Particulars → Particulars | 2nd column → 1st column after Particulars | 990 Mapping (CY) → 990 Mapping (LY)
        
        4. **Download** - Get all processed files in a single ZIP archive
        """)
    
    # File Upload Section
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">📂 File Upload</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="upload-container">
            <div class="upload-title">📁 Prior Year Workbooks</div>
            <div class="upload-desc">Upload one or more Excel files</div>
        </div>
        """, unsafe_allow_html=True)
        
        input_files = st.file_uploader(
            "Choose files",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            key="input_files",
            help="Select one or more Excel workbooks from the prior year",
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("""
        <div class="upload-container">
            <div class="upload-title">📄 Blank Template</div>
            <div class="upload-desc">Upload a single template file</div>
        </div>
        """, unsafe_allow_html=True)
        
        template_file = st.file_uploader(
            "Choose template",
            type=['xlsx', 'xls'],
            accept_multiple_files=False,
            key="template_file",
            help="Select one blank Excel template that will be used for all input files",
            label_visibility="collapsed"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Update stats
    st.session_state.stats['total_files'] = len(input_files) if input_files else 0
    st.session_state.stats['templates'] = 1 if template_file else 0
    
    # Processing section
    if input_files and template_file:
        st.success(f"Ready to process {len(input_files)} file(s) using template: {template_file.name}")
        
        # File processing information
        with st.expander("📋 Processing Preview", expanded=False):
            st.write(f"**Template:** `{template_file.name}`")
            st.write(f"**Input files to process:**")
            for i, input_file in enumerate(input_files):
                st.write(f"  {i+1}. `{input_file.name}`")
        
        # Process button
        if st.button("🚀 Process Files", type="primary"):
            process_files(input_files, template_file)
    
    # # Render database status indicator
    # render_db_status()

def process_files(input_files, template_file):
    """Process all input files using the single template and provide ZIP download"""
    
    processor = ExcelProcessor()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_files = []
    total_files = len(input_files)
    
    # Create processing job in MongoDB if connected
    job_id = None
    if st.session_state.get('db_connected', False):
        db_manager = st.session_state.db_manager
        job_id = db_manager.create_processing_job(
            session_id=st.session_state.session_id,
            input_files=[f.name for f in input_files],
            template_file=template_file.name,
            metadata={'total_files': total_files}
        )
        
        db_manager.log_action(
            'processing_started',
            {'job_id': job_id, 'total_files': total_files},
            st.session_state.session_id
        )
    
    # Validate template file first
    if not validate_excel_file(template_file):
        st.error(f"Invalid template file: {template_file.name}")
        return
    
    for i, input_file in enumerate(input_files):
        try:
            # Update progress
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Processing {input_file.name}... ({i+1}/{total_files})")
            
            # Validate input file
            if not validate_excel_file(input_file):
                st.error(f"Invalid input file: {input_file.name}")
                continue
            
            # Store file metadata in MongoDB if connected
            if st.session_state.get('db_connected', False):
                db_manager.store_file_metadata(
                    filename=input_file.name,
                    file_content=input_file.getvalue(),
                    file_type='input',
                    metadata={'job_id': job_id}
                )
            
            # Process the file pair
            output_buffer = processor.process_file_pair(input_file, template_file)
            
            if output_buffer:
                # Generate output filename with incremented year
                output_filename = increment_year_in_filename(input_file.name)
                
                processed_files.append({
                    'name': output_filename,
                    'buffer': output_buffer,
                    'original_input': input_file.name,
                    'template_used': template_file.name
                })
                
                # Store output file metadata
                if st.session_state.get('db_connected', False):
                    db_manager.store_file_metadata(
                        filename=output_filename,
                        file_content=output_buffer.getvalue(),
                        file_type='output',
                        metadata={'job_id': job_id, 'source': input_file.name}
                    )
                
                st.success(f"Successfully processed: {input_file.name}")
            else:
                st.error(f"Failed to process: {input_file.name}")
                
        except Exception as e:
            st.error(f"Error processing {input_file.name}: {str(e)}")
            continue
    
    # Complete progress
    progress_bar.progress(1.0)
    status_text.text("Processing complete!")
    
    # Update stats
    st.session_state.stats['processed'] = len(processed_files)
    st.session_state.stats['success_rate'] = int((len(processed_files) / total_files) * 100) if total_files > 0 else 0
    
    # Complete processing job in MongoDB
    if job_id and st.session_state.get('db_connected', False):
        db_manager.complete_processing_job(
            job_id=job_id,
            processed_count=len(processed_files),
            failed_count=total_files - len(processed_files),
            output_files=[f['name'] for f in processed_files]
        )
        
        # Update analytics
        db_manager.update_daily_analytics('files_processed', len(processed_files))
        db_manager.update_daily_analytics('jobs_completed', 1)
        
        db_manager.log_action(
            'processing_completed',
            {
                'job_id': job_id,
                'processed': len(processed_files),
                'failed': total_files - len(processed_files)
            },
            st.session_state.session_id
        )
    
    # Display results and download ZIP
    if processed_files:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-title">📥 Download Results</h2>', unsafe_allow_html=True)
        
        # Create ZIP file with all processed files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in processed_files:
                zip_file.writestr(file_info['name'], file_info['buffer'].getvalue())
        
        zip_buffer.seek(0)
        
        # Display file list
        with st.expander("📋 Files in ZIP Package", expanded=True):
            for file_info in processed_files:
                st.write(f"**{file_info['name']}**")
                st.caption(f"Source: {file_info['original_input']} | Template: {file_info['template_used']}")
        
        # Single download button for ZIP
        current_date = datetime.now().strftime("%Y%m%d")
        zip_filename = f"Processed_Excel_Files_{current_date}.zip"
        
        st.download_button(
            label="📦 Download All Files as ZIP",
            data=zip_buffer.getvalue(),
            file_name=zip_filename,
            mime="application/zip",
            type="primary"
        )
        
        st.success(f"Successfully processed {len(processed_files)} out of {total_files} file(s)")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error("No files were successfully processed. Please check your input files and try again.")

if __name__ == "__main__":
    main()