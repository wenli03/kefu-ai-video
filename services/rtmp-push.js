// RTMP Push Utility — pushes video+audio to SRS
const NodeMediaServer = require('node-media-server');
const fs = require('fs');

const room = process.argv[process.argv.indexOf('--room') + 1];
const videoFile = process.argv[process.argv.indexOf('--video') + 1];
const audioFile = process.argv[process.argv.indexOf('--audio') + 1];

if (!room || !videoFile) {
    console.error('Usage: node rtmp-push.js --room <name> --video <file> [--audio <file>]');
    process.exit(1);
}

console.log(`[RTMP Push] Room: ${room}, Video: ${videoFile}, Audio: ${audioFile || 'none'}`);

// Read video file and push via RTMP using ffmpeg-static or child_process
const { spawn } = require('child_process');

const args = ['-re', '-i', videoFile];
if (audioFile && fs.existsSync(audioFile)) {
    args.push('-i', audioFile);
    args.push('-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest');
} else {
    args.push('-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'copy');
}
args.push('-f', 'flv', `rtmp://localhost:1935/live/${room}`);

console.log(`[RTMP Push] Running ffmpeg ${args.join(' ')}`);

const ffmpeg = spawn('ffmpeg', args, { stdio: 'inherit' });
ffmpeg.on('close', (code) => {
    console.log(`[RTMP Push] Finished with code ${code}`);
    process.exit(code);
});
ffmpeg.on('error', (err) => {
    console.error(`[RTMP Push] Error: ${err.message}`);
    process.exit(1);
});
