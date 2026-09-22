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

# --- CSS STYLING AF DE 2 STORE KNAPPER ---
st.markdown("""
    <style>
    /* Styling af de to store centraliserede menu-knapper */
    div.stButton > button {
        width: 300px !important;       /* Ca. 10 cm i bredden på skærmen */
        height: 150px !important;      /* Ca. 5 cm i højden på skærmen */
        font-size: 100px !important;    /* Stor, læsbar tekst */
        font-weight: bold !important;
        border-radius: 20px !important;
        border: 4px solid #dee2e6 !important;
        background-color: #f8f9fa !important;
        color: #212529 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease-in-out !important;
        white-space: normal !important; /* Tillader tekstombrydning hvis nødvendigt */
    }
    
    /* Effekt når musen holdes over menu-knapperne */
    div.stButton > button:hover {
        border-color: #2bc473 !important;
        background-color: #e8f7ee !important;
        color: #229a59 !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1) !important;
    }

    /* Gør den aktive knap permanent grøn og fremhævet */
    .active-btn div.stButton > button {
        background-color: #2bc473 !important;
        color: white !important;
        border-color: #229a59 !important;
    }
    
    /* Styling af den mindre "Aktion"-knap inde i sektionerne (Analyser / Saml) */
    div[data-testid="stForm"] div.stButton > button, 
    .action-container div.stButton > button {
        width: auto !important;
        height: auto !important;
        font-size: 16px !important;
        background-color: #2bc473 !important;
        color: white !important;
        padding: 0.5rem 2rem !important;
        border: none !important;
    }
    div[data-testid="stForm"] div.stButton > button:hover,
    .action-container div.stButton > button:hover {
        background-color: #229a59 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)


# --- NAVIGATION LOGIK VIA SESSION STATE ---
# Vi bruger session_state til at huske, hvilken menu der er aktiv, uden at siden glemmer det ved upload
if "valgt_menu" not in st.session_state:
    st.session_state.valgt_menu = None  # Starttilstand (intet valgt endnu)

# Lav 5 kolonner for at centrere de to store knapper i midten af skærmen
# Kolonne 2 og 4 holder knapperne, kolonne 1, 3 og 5 skaber luft/centrering
col1, col2, col3, col4, col5 = st.columns([1, 2, 0.2, 2, 1])

with col2:
    # Hvis denne menu er valgt, giv containeren en speciel CSS-klasse for at gøre den grøn
    if st.session_state.valgt_menu == "split":
        st.markdown('<div class="active-btn">', unsafe_allow_html=True)
    
    if st.button("✂️\n\nSplit PDF\n(Intelligent)"):
        st.session_state.valgt_menu = "split"
        st.rerun()
        
    if st.session_state.valgt_menu == "split":
        st.markdown('</div>', unsafe_allow_html=True)

with col4:
    if st.session_state.valgt_menu == "saml":
        st.markdown('<div class="active-btn">', unsafe_allow_html=True)
        
    if st.button("➕\n\nSaml PDFer\n(Merge)"):
        st.session_state.valgt_menu = "saml"
        st.rerun()
        
    if st.session_state.valgt_menu == "saml":
        st.markdown('</div>', unsafe_allow_html=True)

# Tilføj en vandret skillelinje under menuen
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
            
            # Container-klasse til at styre, at denne knap IKKE bliver 5x10 cm stor
            st.markdown('<div class="action-container">', unsafe_allow_html=True)
            analyser_knap = st.button("Analyser og Split PDF")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if analyser_knap:
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
                except Exception as e:st.error(f"Kunne ikke samle filerne: {e}")
