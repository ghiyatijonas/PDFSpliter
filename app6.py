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

# --- DESIGN AF KNAPPER (RETTET TIL STREMLIT STANDARD STIL) ---
st.markdown("""
    <style>
    /* 1. FORCE DE TO MENU-KNAPPER I TOPPEN TIL AT VÆRE STORE */
    .menu-box button {
        width: 380px !important;       /* Ca. 10 cm i bredden */
        height: 190px !important;      /* Ca. 5 cm i højden */
        font-size: 24px !important;    /* Stor, læsbar tekst */
        font-weight: bold !important;
        border-radius: 12px !important;
        border: 2px solid #dee2e6 !important;
        background-color: #f8f9fa !important;
        color: #212529 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease-in-out !important;
        white-space: normal !important;
        display: block !important;
    }
    
    .menu-box button:hover {
        border-color: #2bc473 !important;
        background-color: #e8f7ee !important;
        color: #229a59 !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1) !important;
    }

    /* Gør den aktive menu-knap permanent grøn */
    .active-btn button {
        background-color: #2bc473 !important;
        color: white !important;
        border-color: #229a59 !important;
    }
    
    /* 2. NULSTIL AKTION-KNAPPERNE SÅ DE MATCHER UPLOAD-KNAPPEN (STANDARD GRÅ) */
    .action-container button {
        width: auto !important;        /* Almindelig bredde */
        height: auto !important;       /* Almindelig højde */
        font-size: 14px !important;    /* Matcher Streamlit standard */
        font-weight: normal !important;
        background-color: rgb(243, 244, 246) !important; /* Præcis samme grå som Upload-knappen */
        color: rgb(49, 51, 63) !important;             /* Standard mørk tekstfarve */
        padding: 0.25rem 0.75rem !important;           /* Standard knap-luft */
        border-radius: 0.5rem !important;              /* Afrundede hjørner som upload */
        border: 1px solid rgba(49, 51, 63, 0.2) !important; /* Diskret kant */
        box-shadow: none !important;
        transform: none !important;
    }
    
    .action-container button:hover {
        border-color: #2bc473 !important; /* Grøn kant ved hover for at vise aktivitet */
        color: #229a59 !important;
        background-color: rgb(243, 244, 246) !important;
    }
    </style>
""", unsafe_allow_html=True)


# --- NAVIGATION LOGIK VIA SESSION STATE ---
if "valgt_menu" not in st.session_state:
    st.session_state.valgt_menu = None

col1, col2, col3, col4, col5 = st.columns([1, 2, 0.2, 2, 1])

with col2:
    if st.session_state.valgt_menu == "split":
        st.markdown('<div class="menu-box active-btn">', unsafe_allow_html=True)
    else:
        st.markdown('<div class="menu-box">', unsafe_allow_html=True)
        
    if st.button("✂️\n\nSplit PDF\n(Intelligent)"):
        st.session_state.valgt_menu = "split"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    if st.session_state.valgt_menu == "saml":
        st.markdown('<div class="menu-box active-btn">', unsafe_allow_html=True)
    else:
        st.markdown('<div class="menu-box">', unsafe_allow_html=True)
        
    if st.button("➕\n\nSaml PDFer\n(Merge)"):
        st.session_state.valgt_menu = "saml"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br><hr><br>", unsafe_allow_html=True)


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
            
            # Action-container sikrer, at knappen bliver lille og grå som upload-knappen
            st.markdown('<div class="action-container">', unsafe_allow_html=True)
            analyser_knap = st.button("Analyser og Split PDF")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if analyser_knap:
                with st.spinner("Scanner sider..."):
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
                        st.error("Kunne ikke finde nogen fakturanumre på siderne.")
                    else:
                        st.success(f"Færdig! Fandt {len(invoice_chunks)} individuelle fakturaer.")
                        
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
                                st.write(f"• **Faktura #{inv_id}**: Indeholder {len(pages)} side(r) (Sider: {[p+1 for p in pages]})")
        except Exception as e:
            st.error(f"Der skete en fejl: {e}")

# --- SEKTION 2: SAML PDF-FILER ---
elif st.session_state.valgt_menu == "saml":
    st.header("Saml flere sider/filer til én PDF")
    st.write("Upload flere PDF-filer. De vil blive samlet i den rækkefølge, du uploader dem.")
    
    uploaded_files = st.file_uploader("Upload de PDF-filer, der skal samles", type=["pdf"], accept_multiple_files=True, key="merger_upload")
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} filer klar til samling.")
        output_filename = st.text_input("Navn på den samlede PDF-fil:", value="samlet_dokument.pdf")
        
        st.markdown('<div class="action-container">', unsafe_allow_html=True)
        saml_knap = st.button("Saml filer nu")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if saml_knap:
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
