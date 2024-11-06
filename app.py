from flask import Flask, render_template, request, redirect, url_for, Response
import yt_dlp
import os
import subprocess
from time import sleep

app = Flask(__name__)

# Global dictionary to track download progress
progress_data = {
    'percentage': '0%',
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']  # Get the URL from the form
        download_type = request.form['download_type']  # Get the download type (audio, video, both)
        return redirect(url_for('formats', url=url, download_type=download_type))  # Redirect to formats page
    
    return render_template('index.html')  # Render the homepage for GET requests

@app.route('/formats', methods=['GET'])
def formats():
    url = request.args.get('url')  # Fetch the YouTube video URL from query parameters
    download_type = request.args.get('download_type')  # Fetch the download type (audio, video, or both)

    # Fetch formats using yt-dlp
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)  # Extract video info without downloading
        formats = info.get('formats', [])  # Get available formats

    # Filter formats based on download type
    if download_type == 'audio':
        formats = [f for f in formats if f['ext'] in ['mp3', 'm4a']]  # Only show mp3 or m4a for audio
    elif download_type == 'video':
        formats = [f for f in formats if f['ext'] in ['mp4', 'webp']]  # Show mp4 and webp for video
    elif download_type == 'video_audio':
        formats = [f for f in formats if f['ext'] == 'mp4']  # Show mp4 for audio + video

    return render_template('formats.html', formats=formats, url=url, download_type=download_type)

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']  # The YouTube URL
    format_id = request.form['format_id']  # The selected format ID
    download_type = request.form['download_type']  # Type: audio, video, or both

    # Set up yt-dlp options
    ydl_opts = {
        'format': format_id,  # Download the format selected by the user
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in the downloads directory
        'progress_hooks': [progress_hook],  # Hook to update progress bar
    }

    # Perform the video download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url)  # Download the selected format
        downloaded_video = ydl.prepare_filename(info)  # Get the path to the downloaded video file

    # If audio and video are requested, combine them (using FFmpeg or similar tool)
    if download_type == 'video_audio':
        # Download the audio stream separately
        ydl_opts['format'] = 'bestaudio'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)  # Download the audio format
            downloaded_audio = ydl.prepare_filename(info)  # Get the path to the downloaded audio file
        
        # Combine audio and video using FFmpeg
        output_file = downloaded_video.replace(".mp4", "_combined.mp4")
        ffmpeg_cmd = [
            'ffmpeg', '-i', downloaded_video, '-i', downloaded_audio,
            '-c:v', 'copy', '-c:a', 'aac', output_file
        ]
        subprocess.run(ffmpeg_cmd)

        # Optionally, clean up the separate video and audio files
        os.remove(downloaded_video)
        os.remove(downloaded_audio)
    else:
        output_file = downloaded_video

    return render_template('complete.html', filename=output_file)

@app.route('/progress')
def progress():
    def generate():
        # Simulate the progress bar response with server-sent events
        while progress_data["percentage"] != "100%":  # Stop once the download hits 100%
            percentage = progress_data['percentage']
            
            # Properly format the output for clean display (percentage only)
            yield f"data: {percentage.strip()}\n\n"
            sleep(1)
        yield "data: Download Complete\n\n"  # Signal that download is complete
    
    return Response(generate(), mimetype='text/event-stream')

# Progress hook to update the global progress dictionary
def progress_hook(d):
    if d['status'] == 'downloading':
        progress_data['percentage'] = d.get('_percent_str', '0%').strip()

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')  # Create a downloads folder if it doesn't exist
    app.run(debug=True)
