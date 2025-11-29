import streamlit as st
import subprocess
import sys
import os
import re
import tempfile
import zipfile
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", 'pydub'])
    from pydub import AudioSegment


def time_to_seconds(time_str):
    """Converte timestamp in secondi"""
    parts = time_str.strip().split(':')
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    elif len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    return 0


def parse_tracklist(tracklist_text):
    """
    Parsa il testo della tracklist e restituisce una lista di tuple (seconds, title)
    Supporta vari formati:
    - 00:00:00 01.Titolo
    - 0:00:00 - Titolo
    - 00:00 Titolo
    """
    tracks = []
    lines = tracklist_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Pattern per catturare timestamp e titolo
        # Supporta formati come: "00:00:00 01.Titolo", "0:00:00 - Titolo", "00:00 Titolo"
        pattern = r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*[-.]?\s*(.+)$'
        match = re.match(pattern, line)
        
        if match:
            time_str = match.group(1)
            title = match.group(2).strip()
            # Rimuove numeri iniziali tipo "01." o "01 "
            title = re.sub(r'^\d+[.\s]+', '', title).strip()
            seconds = time_to_seconds(time_str)
            tracks.append((seconds, title))
    
    return tracks


def split_audio(audio_path, tracks, output_folder, artist="", album=""):
    """Splitta l'audio in tracce separate"""
    # Carica l'audio
    audio = AudioSegment.from_file(audio_path)
    
    split_files = []
    
    for i, (start_seconds, title) in enumerate(tracks):
        start_ms = start_seconds * 1000
        
        # Calcola la fine (inizio della traccia successiva o fine audio)
        if i + 1 < len(tracks):
            end_ms = tracks[i + 1][0] * 1000
        else:
            end_ms = len(audio)
        
        # Estrai il segmento
        segment = audio[start_ms:end_ms]
        
        # Crea nome file sicuro
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        track_num = str(i + 1).zfill(2)
        filename = f"{track_num}. {safe_title}.mp3"
        filepath = os.path.join(output_folder, filename)
        
        # Esporta con tag ID3
        tags = {
            "title": title,
            "track": str(i + 1),
        }
        if artist:
            tags["artist"] = artist
        if album:
            tags["album"] = album
        
        segment.export(filepath, format="mp3", tags=tags)
        split_files.append(filepath)
    
    return split_files


def create_zip(files, zip_path):
    """Crea un file ZIP con tutte le tracce"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return zip_path


# Configurazione pagina Streamlit
st.set_page_config(
    page_title="YouTube Audio Splitter",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Audio Splitter")
st.markdown("Carica un file audio e splittalo in tracce separate usando i timestamp")

# Upload file audio
uploaded_file = st.file_uploader(
    "🎧 Carica file audio",
    type=['mp3', 'wav', 'ogg', 'm4a', 'flac', 'mp4'],
    help="Formati supportati: MP3, WAV, OGG, M4A, FLAC, MP4"
)

# Input tracklist
default_tracklist = """00:00:00 01.街の灯りがやわらぐ頃
00:03:20 02. Lost Frequency
00:06:30 03.Moon Reflections
00:10:31 04. Moonlit Slow Dance
00:14:10 05.しずかな音色
00:17:32 06.Room 203
00:20:46 07. Sleepless Moonlight
00:24:08 08.Moon Reflections
00:28:01 09.記憶のカタチ
00:31:09 10.夜にとけて
00:34:55 11.月影のあとで
00:38:35 12.夜明けのリズム
00:42:05 13.月の記憶
00:45:35 14.ヒカリの手前
00:48:56 15.Blue Reflection
00:52:15 16.月に聴いたSTORY
00:55:18 17.夜空を歩く
00:58:57 18.光の中で瞬く
01:02:29 19.Late Call, No Answer
01:05:26 20. When Silence Turns Gold
01:08:52 21. 光を残して
01:12:17 22. Faint Horizon _ 空の線
01:15:50 23. Before Sunrise
01:19:08 24. 残された音色
01:22:30 25.朝の残響"""

tracklist_text = st.text_area(
    "📝 Tracklist (formato: timestamp titolo)",
    value=default_tracklist,
    height=400,
    help="Inserisci ogni traccia su una riga nel formato: 00:00:00 Titolo"
)

# Opzioni aggiuntive
col1, col2 = st.columns(2)
with col1:
    artist = st.text_input("🎤 Artista (opzionale)", placeholder="Nome artista")
with col2:
    album = st.text_input("💿 Album (opzionale)", placeholder="Nome album")

# Preview tracklist parsata
if tracklist_text:
    tracks = parse_tracklist(tracklist_text)
    if tracks:
        with st.expander(f"📋 Preview: {len(tracks)} tracce trovate", expanded=False):
            for i, (seconds, title) in enumerate(tracks):
                mins, secs = divmod(seconds, 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
                st.text(f"{i+1:02d}. [{time_str}] {title}")

# Pulsante per avviare il processo
if st.button("🚀 Splitta Audio", type="primary", use_container_width=True):
    if not uploaded_file:
        st.error("❌ Carica un file audio")
    elif not tracklist_text:
        st.error("❌ Inserisci la tracklist")
    else:
        tracks = parse_tracklist(tracklist_text)
        if not tracks:
            st.error("❌ Nessuna traccia trovata nella tracklist")
        else:
            # Crea directory temporanea
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    with st.status("🔄 Elaborazione in corso...", expanded=True) as status:
                        # Step 1: Salva file caricato
                        st.write("📥 Caricamento audio...")
                        audio_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(audio_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        st.write(f"✅ Audio caricato: {uploaded_file.name}")
                        
                        # Step 2: Split
                        st.write(f"✂️ Splitting in {len(tracks)} tracce...")
                        output_folder = os.path.join(temp_dir, "tracks")
                        os.makedirs(output_folder, exist_ok=True)
                        
                        split_files = split_audio(
                            audio_path, 
                            tracks, 
                            output_folder,
                            artist=artist,
                            album=album
                        )
                        
                        st.write(f"✅ {len(split_files)} tracce create")
                        
                        # Step 3: Create ZIP
                        st.write("📦 Creazione archivio ZIP...")
                        zip_path = os.path.join(temp_dir, "tracks.zip")
                        create_zip(split_files, zip_path)
                        
                        status.update(label="✅ Completato!", state="complete", expanded=True)
                    
                    # Download button
                    with open(zip_path, "rb") as f:
                        zip_data = f.read()
                    
                    st.success(f"🎉 Download pronto! {len(split_files)} tracce estratte")
                    
                    # Nome ZIP basato sul file originale
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    
                    st.download_button(
                        label="📥 Scarica tutte le tracce (ZIP)",
                        data=zip_data,
                        file_name=f"{base_name}_tracks.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Errore: {str(e)}")
                    st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>
        ⚠️ Assicurati di avere <a href='https://ffmpeg.org/download.html'>FFmpeg</a> installato sul sistema.
    </small>
</div>
""", unsafe_allow_html=True)
