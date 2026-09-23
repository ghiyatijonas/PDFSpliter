import streamlit as st
from pypdf import PdfReader, PdfWriter
import re, io, zipfile

st.set_page_config(page_title="PDF Værktøj", page_icon="📄", layout="wide")
st.title("📄 PDF Faktura Splitter & Samler")

if "menu" not in st.session_state:
    st.session_state.menu = None

params = st.query_params
if "m" in params:
    st.session_state.menu = params["m"]
    st.query_params.clear()
    st.rerun()

act_split = "active" if st.session_state.menu == "split" else ""
act_saml = "active" if st.session_state.menu == "saml" else ""

st.markdown(f"""
    <style>
    .m-container {{ display: flex; justify-content: center; gap: 20px; margin: 20px 0; }}
    .m-btn {{
        width: 350px; height: 150px; font-size: 22px; font-weight: bold;
        border-radius: 12px; border: 2px solid #dee2e6; background-color: #f8f9fa;
        color: #212529; cursor: pointer; display: flex; flex-direction: column;
        align-items: center; justify-content: center; text-decoration: none;
    }}
    .m-btn:hover {{ border-color: #2bc473; background-color: #e8f7ee; color: #229a59; }}
    .m-btn.active {{ background-color: #2bc473; color: white; border-color: #229a59; }}
    .m-btn span {{ font-size: 28px; margin-bottom: 5px; }}
    [data-testid="stFileUploaderDropzone"] button, div.stButton > button, div.stDownloadButton > button {{
        background-color: #2bc473 !important; color: white !important;
        border: none !important; border-radius: 6px !important; padding: 0.5rem 1.5rem !important;
    }}
    [data-testid="stFileUploaderDropzone"] button:hover, div.stButton > button:hover, div.stDownloadButton > button:hover {{
        background-color: #229a59 !important;
    }}
    div.stDownloadButton > button {{ width: 100% !important; font-size: 18px !important; font-weight: bold !important; }}
    </style>
    <div class="m-container">
        <a href="?m=split" target="_self" class="m-btn {act_split}"><span>✂️</span>Split PDF</a>
        <a href="?m=saml" target="_self" class="m-btn {act_saml}"><span>➕</span>Saml PDFer</a>
    </div>
    <br><hr><br>
""", unsafe_allow_html=True)

# 🔍 RETTET FUNKTION: Udtrækker fakturanummeret som en REN tekststreng uden klammer []
def get_inv_num(text):
    clean = " ".join(text.split())
    low = text.lower()
    
    if "fakturanr" in low:
        col = re.findall(r":\s*(\d+)", text)
        if col: 
            return str(col[0]).strip() # Snupper det første rene tal i listen
            
    pats = [r"(?:faktura|invoice)(?:\s*nr|\s*no|\s*nummer)?[:.\s]*#?\s*(\d+)", r"(?:inv|fak)[:.\s]*#?\s*(\d+)"]
    for p in pats:
        m = re.search(p, clean, re.IGNORECASE)
        if m: 
            return str(m.group(1)).strip()
            
    if "faktura" in low or "invoice" in low:
        pot = re.findall(r"\b\d{4,8}\b", clean)
        if pot: 
            return str(pot[0]).strip()
    return None

if st.session_state.menu == "split":
    st.header("Split fakturaer med intelligent genkendelse")
    l_col, r_col = st.columns(2)
    with l_col:
        st.subheader("1. Vælg og start")
        up = st.file_uploader("Upload samlet PDF", type=["pdf"], key="split_up")
        if up and st.button("🚀 Analyser og Split PDF"):
            st.session_state.do_split = True
    with r_col:
        st.subheader("2. Resultat")
        if "do_split" in st.session_state and up:
            with st.spinner("Scanner..."):
                reader = PdfReader(up)
                chunks = []
                for idx, page in enumerate(reader.pages):
                    inv_id = get_inv_num(page.extract_text() or "")
                    if inv_id: chunks.append((inv_id, [idx]))
                    elif chunks: chunks[-1][1].append(idx)
                    else: chunks.append(("ukendt", [idx]))
                if chunks:
                    st.success(f"Fandt {len(chunks)} fakturaer.")
                    z_buf = io.BytesIO()
                    with zipfile.ZipFile(z_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for i_id, p_idxs in chunks:
                            writer = PdfWriter()
                            for p in p_idxs: writer.add_page(reader.pages[p])
                            p_buf = io.BytesIO()
                            writer.write(p_buf)
                            
                            # Sikrer rene og pæne filnavne i ZIP-filen
                            clean_id = re.sub(r'[\\/*?:"<>|]', "", i_id)
                            name = f"faktura_{clean_id}_{len(p_idxs)}sider.pdf" if len(p_idxs) >= 2 else f"faktura_{clean_id}.pdf"
                            zf.writestr(name, p_buf.getvalue())
                    z_buf.seek(0)
                    st.download_button(label=f"🎁 Download alle {len(chunks)} fakturaer (ZIP)", data=z_buf, file_name="fakturaer.zip", mime="application/zip")

elif st.session_state.menu == "saml":
    st.header("Saml flere filer til én PDF")
    l_col, r_col = st.columns(2)
    with l_col:
        st.subheader("1. Vælg filer")
        ups = st.file_uploader("Upload PDF-filer", type=["pdf"], accept_multiple_files=True, key="saml_ups")
        if ups:
            out_name = st.text_input("Filnavn:", value="samlet.pdf")
            if st.button("🔗 Saml filer nu"):
                st.session_state.do_saml = True
    with r_col:
        st.subheader("2. Download")
        if "do_saml" in st.session_state and ups:
            try:
                writer = PdfWriter()
                for f in ups:
                    for p in PdfReader(f).pages: writer.add_page(p)
                out_buf = io.BytesIO()
                writer.write(out_buf)
                out_buf.seek(0)
                st.success("Filer lagt sammen!")
                st.download_button(label="📥 Download samlet PDF", data=out_buf, file_name=out_name, mime="application/pdf")
            except Exception as e:
                st.error(f"Fejl: {e}")
