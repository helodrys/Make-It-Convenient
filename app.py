from flask import Flask, render_template, request, send_file
from pytubefix import YouTube #Swapping these 2 somehow is the problem fixer lmao 
# from pytubefix.cli import on_progress
# from pytube import YouTube
from pytube.cli import on_progress
import os
from pydub import AudioSegment
import qrcode
import io
from pytube.innertube import _default_clients
from pytube import cipher
import re
from pytube.exceptions import RegexMatchError
from moviepy.editor import VideoFileClip, AudioFileClip
import subprocess
from typing import Optional
import os

# po_token = os.getenv("PO_TOKEN")
# visitor_data = os.getenv("VISITOR_DATA") At this point what's the point lmao youtube too good

_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]



def get_throttling_function_name(js: str) -> str:
    """Extract the name of the function that computes the throttling parameter.

    :param str js:
        The contents of the base.js asset file.
    :rtype: str
    :returns:
        The name of the function used to compute the throttling parameter.
    """
    function_patterns = [
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*'
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])\([a-z]\)',
    ]
    #logger.debug('Finding throttling function name')
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            #logger.debug("finished regex search, matched: %s", pattern)
            if len(function_match.groups()) == 1:
                return function_match.group(1)
            idx = function_match.group(2)
            if idx:
                idx = idx.strip("[]")
                array = re.search(
                    r'var {nfunc}\s*=\s*(\[.+?\]);'.format(
                        nfunc=re.escape(function_match.group(1))),
                    js
                )
                if array:
                    array = array.group(1).strip("[]").split(",")
                    array = [x.strip() for x in array]
                    return array[int(idx)]

    raise RegexMatchError(
        caller="get_throttling_function_name", pattern="multiple"
    )

cipher.get_throttling_function_name = get_throttling_function_name

app = Flask(__name__)

def change_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)
@app.route('/')
def hello():
    return render_template("index.html")
@app.route('/soundtovideo')
def sound_to_video():
    return render_template("soundtovideo.html")
@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    
    if file.filename == '':
        return "No file selected"
    temp_file_path = os.path.join("uploads", file.filename)
    file.save(temp_file_path)

    mp3_file_path = os.path.splitext(temp_file_path)[0] + '.mp3'
    audio = AudioSegment.from_file(temp_file_path, format='mp4')
    audio.export(mp3_file_path, format='mp3')

    return send_file(mp3_file_path, as_attachment=True)


@app.route('/convert_qrcode', methods=["POST"])
def convert_qrcode():
    link = request.form.get("link")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

@app.route('/qrcode')
def qr_code():
    return render_template("qrcode.html")

def change_filename_e(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)
@app.route("/convert", methods=["POST"])

def convert():
    convert_type = request.form.get("converter")
    link = request.form.get("link")
    
    try:
        yt = YouTube(link) 
        
        final_path = None

        if convert_type == "mp3":
            audio_stream = yt.streams.filter(only_audio=True).first()
            final_path = audio_stream.download(output_path="downloads", filename=f"{yt.title}.mp3")
        
        elif convert_type in ["mp4", "Pure_screen"]:
            video_stream = yt.streams.filter(res="1080p", file_extension='mp4').first() or yt.streams.filter(file_extension='mp4').order_by('resolution').last()
            video_path = video_stream.download(output_path="downloads", filename=f"{yt.title}_video.mp4")

            if convert_type == "mp4":
                audio_stream = yt.streams.filter(only_audio=True).first()
                audio_path = audio_stream.download(output_path="downloads", filename=f"{yt.title}_audio.mp4")
                #ffmpeg is 10x faster than moviepy fr
                title = yt.title
                final_path = f"downloads/{change_filename_e(title)}_final.mp4"
                subprocess.run([
                    'ffmpeg',
                    '-i', video_path,
                    '-i', audio_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-strict', 'experimental',
                    final_path
                ], check=True)
            
            elif convert_type == "Pure_screen":
                final_path = video_path
        return send_file(final_path, as_attachment=True)

    except Exception as e:
        return str(e)