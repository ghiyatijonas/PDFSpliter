import streamlit as st
import pypdf
from pypdf import PdfReader, PdfWriter  # PdfMerger er fjernet og erstattet med PdfWriter
import re
import io
import zipfile

st.set_page_config(page_title="PDF Faktura Værktøj", page_icon="📄", layout="wide")

st.title("📄 PDF Faktura Splitter & Samler")
st.write("Dette værktøj splitter automatisk store PDF-filer baseret på fakturanumre. Den understøtter **mange forskellige formater og spalte-layouts** på samme tid.")

tab1, tab2 = st.tabs(["✂️ Split PDF (Intelligent Genkendelse)", "➕ Saml PDF-filer"])

# HJÆLPEFUNKTION: Den intelligente søgemaskine til fakturanumre
def find_invoice_number(text):
    clean_text = " ".join(text.split())
    text_lowercase = text.lower()
    
    # 1. TJEK: Dit specifikke spalte-layout (Tekst til venstre, : tal til højre)
    if "fakturanr" in text_lowercase:
        colon_numbers = re.findall(r":\s*(\d+)", text)
        if colon_numbers:
            return colon_numbers[0]
            
    # 2. TJEK: Klassiske standardformater på samme linje (Danske og Engelske)
    standard_patterns = [
        r"(?:faktura|invoice)(?:\s*nr|\s*no|\s*nummer)?[:.\s]*#?\s*(\d+)",
        r"(?:inv|fak)[:.\s]*#?\s*(\d+)"
    ]
    for pattern in standard_patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            return match.group(1)
            
    # 3. TJEK: Hvis ordet findes, men tallet er skubbet (Fallback)
    if "faktura" in text_lowercase or "invoice" in text_lowercase:
        potential_numbers = re.findall(r"\b\d{4,8}\b", clean_text)
        if potential_numbers:
            return potential_numbers[0]
            
    return None


# TAB 1: SPLIT PDF
with tab1:
    st.header("Split fakturaer med intelligent genkendelse")
    uploaded_file = st.file_uploader("Upload din samleden PDF-fil", type=["pdf"], key="splitter_upload")
    
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            st.info(f"Filen blev indlæst korrekt. Total antal sider: {total_pages}")
            
            if st.button("Analyser og Split PDF", type="primary"):
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
                        
                        # Opret ZIP
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
                                if num_pages >= 2:
                                    filename = f"faktura_{inv_id}_{num_pages}sider.pdf"
                                else:
                                    filename = f"faktura_{inv_id}.pdf"
                                    
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

# TAB 2: SAML PDF-FILER
with tab2:
    st.header("Saml flere sider/filer til én PDF")
    st.write("Upload flere PDF-filer. De vil blive samlet i den rækkefølge, du uploader dem.")
    
    uploaded_files = st.file_uploader("Upload de PDF-filer, der skal samles", type=["pdf"], accept_multiple_files=True, key="merger_upload")
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} filer klar til samling.")
        output_filename = st.text_input("Navn på den samlede PDF-fil:", value="samlet_dokument.pdf")
        
        if st.button("Saml filer nu", type="primary"):
            with st.spinner("Samler dine PDF-filer..."):
                try:
                    # HER ER RETTELSEN: Vi bruger PdfWriter til at samle (appende) filer i stedet
                    writer = PdfWriter()
                    for f in uploaded_files:
                        writer.append(f)
                    
                    merged_buffer = io.BytesIO()
                    writer.write(merged_buffer)
                    merged_buffer.seek(0)
                    writer.close()
                    
                    st.success("Filerne blev samlet med succes!")
                    
                    st.download_button(
                        label="📥 Download samlet PDF",
                        data=merged_buffer,
                        file_name=output_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Kunne ikke samle filerne: {e}")
