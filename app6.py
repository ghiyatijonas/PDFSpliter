import streamlit as st
import pypdf
from pypdf import PdfReader, PdfWriter
import re
import io
import zipfile

# Sæt siden til wide layout
st.set_page_config(page_title="PDF Faktura Værktøj", page_icon="📄", layout="wide")

st.title("📄 PDF Faktura Splitter & Samler")
st.write("**Dette værktøj splitter automatisk store PDF-filer baseret på fakturanumre, eller samler flere filer til én.**")

# initialiser session state navigation, hvis det ikke findes
if "valgt_menu" not in st.session_state:
    st.session_state.valgt_menu = None

# --- PARSE QUERY PARAMS (Modtag klik fra de store HTML knapper) ---
# Streamlits knapper i HTML sender parametre via URL'en når der klikkes
params = st.query_params
if "menu" in params:
    st.session_state.valgt_menu = params["menu"]
    # Rens URL med det samme så siden ikke reloader i uendelighed
    st.query_params.clear()
    st.rerun()

# --- GENERER DE 2 GIGANTISKE MENU-KNAPPER VIA RENT HTML/CSS ---
# Dette er 100% isoleret fra Streamlits egne knapper, så intet bliver blandet sammen
is_split_active = "active" if st.session_state.valgt_menu == "split" else ""
is_saml_active = "active" if st.session_state.valgt_menu == "saml" else ""

st.markdown(f"""
    <style>
    .menu-container {{
        display: flex;
        justify-content: center;
        gap: 20px;
        margin: 30px 0;
    }}
    .huge-menu-btn {{
        width: 380px;
        height: 190px;
        font-size: 24px;
        font-weight: bold;
        border-radius: 12px;
        border: 2px solid #dee2e6;
        background-color: #f8f9fa;
        color: #212529;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        text-align: center;
        line-height: 1.4;
    }}
    .huge-menu-btn:hover {{
        border-color: #2bc473;
        background-color: #e8f7ee;
        color: #229a59;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }}
    /* Hvis knappen er aktiv, bliver den permanent flot grøn */
    .huge-menu-btn.active {{
        background-color: #2bc473;
        color: white;
        border-color: #229a59;
    }}
    .huge-menu-btn span {{
        font-size: 32px;
        margin-bottom: 10px;
    }}
    </style>
    
    <div class="menu-container">
        <a href="?menu=split" target="_self" class="huge-menu-btn {is_split_active}">
            <span>✂️</span>Split PDF<br><small style="font-size:14px; font-weight:normal;">(Intelligent)</small>
        </a>
        <a href="?menu=saml" target="_self" class="huge-menu-btn {is_saml_active}">
            <span>➕</span>Saml PDFer<br><small style="font-size:14px; font-weight:normal;">(Merge)</small>
        </a>
    </div>
    <br><hr><br>
""", unsafe_allow_html=True)


# --- HJÆLPEFUNKTION TIL FAKTURA-SØGNING ---
def find_invoice_number(text):
    clean_text = " ".join(text.split())
    text_lowercase = text.lower()
    
    if "fakturanr" in text_lowercase:
        colon_numbers = re.findall(r":\s*(\d+)", text)
        if colon_numbers:
            return colon_numbers[0]
            
    standard_patterns = [
        r"(?:faktura|invoice)(?:\s*nr|\s*no|\s*nummer)?[:.\s]*#?\s*(\d+)",
        r"(?:inv|fak)[:.\s]*#?\s*(\d+)"
    ]
    for pattern in standard_patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            return match.group(1)
            
    if "faktura" in text_lowercase or "invoice" in text_lowercase:
        potential_numbers = re.findall(r"\b\d{4,8}\b", clean_text)
        if potential_numbers:
            return potential_numbers[0]
            
    return None


# --- SEKTION 1: SPLIT PDF ---
if st.session_state.valgt_menu == "split":
    st.header("Split fakturaer med intelligent genkendelse")
    uploaded_file = st.file_uploader("Upload din samlede PDF-fil", type=["pdf"], key="splitter_upload")
    
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            st.info(f"Filen blev indlæst korrekt. Total antal sider: {total_pages}")
            
            # Da vi ikke længere har global CSS-støj, vil denne knap være helt standard grå og matche upload
            if st.button("Analyser og Split PDF"):
                with st.spinner("Scanner sider med den indbyggede intelligente søgemaskine..."):
                    invoice_chunks = []
                    
                    for idx, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        inv_id = find_invoice_number(text)
                        
                        if inv_id:
                            invoice_chunks.append((inv_id, [idx]))
                        else:
                            if invoice_chunks:
                                invoice_chunks[-1][1].append(idx)
                            else:
                                invoice_chunks.append(("ukendt_faktura", [idx]))
                    
                    if not invoice_chunks:
                        st.error("Kunne ikke finde nogen fakturanumre på siderne. Tjek om PDF'en indeholder læsbar tekst.")
                    else:
                        st.success(f"Færdig! Fandt {len(invoice_chunks)} individuelle fakturaer i dokumentet.")
                        
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for inv_id, page_indices in invoice_chunks:
                                writer = PdfWriter()
                                for p_idx in page_indices:
                                    writer.add_page(reader.pages[p_idx])
                                
                                pdf_buffer = io.BytesIO()
                                writer.write(pdf_buffer)
                                pdf_buffer.seek(0)
                                
                                num_pages = len(page_indices)
                                filename = f"faktura_{inv_id}_{num_pages}sider.pdf" if num_pages >= 2 else f"faktura_{inv_id}.pdf"
                                zip_file.writestr(filename, pdf_buffer.getvalue())
                        
                        zip_buffer.seek(0)
                        
                        st.download_button(
                            label="🎁 Download som ZIP",
                            data=zip_buffer,
                            file_name="splittede_fakturaer.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                        
                        with st.expander("Se detaljeret oversigt over opdelingen"):
                            for inv_id, pages in invoice_chunks:
                                st.write(f"• **Faktura #{inv_id}**: Indeholder {len(pages)} side(r) (Sider i alt: {[p+1 for p in pages]})")
        except Exception as e:
            st.error(f"Der skete en fejl under behandlingen af PDF'en: {e}")

# --- SEKTION 2: SAML PDF-FILER ---
elif st.session_state.valgt_menu == "saml":
    st.header("Saml flere sider/filer til én PDF")
    st.write("Upload flere PDF-filer. De vil blive samlet i den rækkefølge, du uploader dem.")
    
    uploaded_files = st.file_uploader("Upload de PDF-filer, der skal samles", type=["pdf"], accept_multiple_files=True, key="merger_upload")
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} filer klar til samling.")
        output_filename = st.text_input("Navn på den samlede PDF-fil:", value="samlet_dokument.pdf")
        
        if st.button("Saml filer nu"):
            with st.spinner("Samler dine PDF-filer..."):
                try:
                    writer = PdfWriter()
                    for uploaded_file in uploaded_files:
                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            writer.add_page(page)
                    
                    output_buffer = io.BytesIO()
                    writer.write(output_buffer)
                    output_buffer.seek(0)
                    
                    st.success("PDF-filerne er lagt sammen!")
                    st.download_button(
                        label="📥 Download samlet PDF",
                        data=output_buffer,
                        file_name=output_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Kunne ikke samle filerne: {e}")
