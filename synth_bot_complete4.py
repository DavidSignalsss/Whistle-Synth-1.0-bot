import os
import numpy as np
from scipy.io.wavfile import write
from pydub import AudioSegment
from scipy.signal import butter, lfilter
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import librosa

TOKEN = "8398854587:AAFZ7BemReu9whSqAnUieZD3AurYzJgJEcs"
os.environ["IMAGEIO_FFMPEG_EXE"] = r"C:\\ffmpeg\\bin\\ffmpeg.exe"  # Change path if needed

# ---- Default analog parameters ----
ATTACK = 0.04
DECAY = 0.08
SUSTAIN = 0.8
RELEASE = 0.22
MIN_CUTOFF = 800
MAX_CUTOFF = 3200
LFO_FREQ = 5
LFO_DEPTH = 0.01

# ---- ADSR ENVELOPE ----
def adsr_envelope(length, fs, attack=ATTACK, decay=DECAY, sustain=SUSTAIN, release=RELEASE):
    a = int(attack * fs)
    d = int(decay * fs)
    r = int(release * fs)
    s = length - (a + d + r)
    envelope = np.concatenate([
        np.linspace(0, 1, a, endpoint=False),
        np.linspace(1, sustain, d, endpoint=False),
        np.full(max(s, 0), sustain),
        np.linspace(sustain, 0, r, endpoint=True)
    ][:length])
    if len(envelope) < length:
        envelope = np.pad(envelope, (0, length - len(envelope)))
    return envelope

# ---- DYNAMIC LOWPASS FILTER ----
def dynamic_lowpass(signal, fs, min_cutoff=MIN_CUTOFF, max_cutoff=MAX_CUTOFF):
    n = len(signal)
    cutoff_vals = np.linspace(min_cutoff, max_cutoff, n)
    out = np.zeros_like(signal)
    chunk_size = 512
    for i in range(0, n, chunk_size):
        cutoff = cutoff_vals[i]
        cutoff = min(max(cutoff, 10), fs / 2 - 100)
        try:
            b, a = butter(2, cutoff / (fs / 2), btype='low')
            out[i:i + chunk_size] = lfilter(b, a, signal[i:i + chunk_size])
        except:
            out[i:i + chunk_size] = signal[i:i + chunk_size]
    return out

# ---- LFO FOR PITCH MOD ----
def lfo(length, fs, freq=LFO_FREQ, depth=LFO_DEPTH):
    t = np.arange(length) / fs
    return 1 + depth * np.sin(2 * np.pi * freq * t)

# ---- MAIN SYNTH FUNCTION ----
def sintetizar_melodia_continua(path_wav, wave_type="sine", fs=44100, hop_length=256, user_params=None):
    y, sr = librosa.load(path_wav, sr=fs)
    y = y / (np.max(np.abs(y)) + 1e-9)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7'),
        sr=sr,
        hop_length=hop_length
    )
    f0 = np.nan_to_num(f0)
    synth = np.zeros(len(y))

    params = user_params if user_params else {
        "attack": ATTACK, "decay": DECAY, "sustain": SUSTAIN, "release": RELEASE,
        "min_cutoff": MIN_CUTOFF, "max_cutoff": MAX_CUTOFF, "lfo_freq": LFO_FREQ, "lfo_depth": LFO_DEPTH
    }

    envelope = adsr_envelope(len(synth), fs, params["attack"], params["decay"], params["sustain"], params["release"])
    lfo_mod = lfo(len(synth), fs, params["lfo_freq"], params["lfo_depth"])

    for t, freq in enumerate(f0):
        if freq > 0:
            start = t * hop_length
            end = min((t + 1) * hop_length, len(y))
            ts = np.arange(end - start)
            freq_modulated = freq * lfo_mod[start:end]
            if wave_type == "sine":
                synth[start:end] = np.sin(2 * np.pi * freq_modulated * ts / fs)
            elif wave_type == "square":
                synth[start:end] = np.sign(np.sin(2 * np.pi * freq_modulated * ts / fs))
            elif wave_type == "saw":
                synth[start:end] = 2 * (ts * freq_modulated / fs - np.floor(ts * freq_modulated / fs + 0.5))

    synth *= envelope
    synth = dynamic_lowpass(synth, fs, params["min_cutoff"], params["max_cutoff"])

    if np.max(np.abs(synth)) > 0:
        synth = (0.9 * synth / np.max(np.abs(synth)) * 32767).astype(np.int16)
    else:
        synth = synth.astype(np.int16)

    i = 1
    while os.path.exists(f"WhistleSynth_Audio_{i}.wav"):
        i += 1
    path_output = f"WhistleSynth_Audio_{i}.wav"
    write(path_output, fs, synth)
    return path_output

# ---- WAVEFORM MENU ----
async def menu_ondas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sine", callback_data='sine')],
        [InlineKeyboardButton("Square", callback_data='square')],
        [InlineKeyboardButton("Sawtooth", callback_data='saw')],
    ]
    await update.message.reply_text(
        "🎚 Select the waveform to simulate your whistle/humming:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def onda_seleccionada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    onda = query.data
    context.user_data['wave_type'] = onda
    await query.edit_message_text(
        f"🔊 Waveform selected: {onda}. Now send a voice message with your whistle or humming."
    )

# ---- SETTINGS MENU AND HANDLERS ----
async def ajustes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_vals = context.user_data.get("synth_params", {
        "attack": ATTACK, "decay": DECAY, "sustain": SUSTAIN, "release": RELEASE,
        "min_cutoff": MIN_CUTOFF, "max_cutoff": MAX_CUTOFF, "lfo_freq": LFO_FREQ, "lfo_depth": LFO_DEPTH
    })
    context.user_data["synth_params"] = user_vals
    kb = [
        [
            InlineKeyboardButton("Attack", callback_data='set_attack'),
            InlineKeyboardButton("Decay", callback_data='set_decay'),
        ],
        [
            InlineKeyboardButton("Sustain", callback_data='set_sustain'),
            InlineKeyboardButton("Release", callback_data='set_release')
        ],
        [
            InlineKeyboardButton("Min Cutoff", callback_data='set_min_cutoff'),
            InlineKeyboardButton("Max Cutoff", callback_data='set_max_cutoff')
        ],
        [
            InlineKeyboardButton("LFO Freq", callback_data='set_lfo_freq'),
            InlineKeyboardButton("LFO Depth", callback_data='set_lfo_depth')
        ],
        [InlineKeyboardButton("Show current values", callback_data='see_vals')],
    ]
    if update.message:
        await update.message.reply_text(
            "🎛 Adjust analog synth parameters (choose one to modify):",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        query = update.callback_query
        await query.edit_message_text(
            "🎛 Adjust analog synth parameters (choose one to modify):",
            reply_markup=InlineKeyboardMarkup(kb)
        )

async def ajustar_parametro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    param = query.data.replace('set_', '')
    valores = context.user_data["synth_params"]
    ranges = {
        "attack": (0.01, 0.5, 0.01),
        "decay": (0.01, 0.5, 0.01),
        "sustain": (0.3, 1.0, 0.05),
        "release": (0.05, 0.5, 0.01),
        "min_cutoff": (100, 3000, 100),
        "max_cutoff": (500, 6000, 100),
        "lfo_freq": (1, 15, 1),
        "lfo_depth": (0.0, 0.10, 0.01)
    }
    minv, maxv, step = ranges[param]
    valact = valores[param]
    kb = [
        [
            InlineKeyboardButton("➖", callback_data=f'down_{param}'),
            InlineKeyboardButton(f"Value: {valact:.2f}", callback_data='noop'),
            InlineKeyboardButton("➕", callback_data=f'up_{param}')
        ],
        [InlineKeyboardButton("⏎ Back to settings", callback_data='ajustes_menu')]
    ]
    await query.edit_message_text(
        f"🔧 Modify {param} (range: {minv}-{maxv}):",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def modificar_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    datos = query.data.split('_')
    accion = datos[0]
    param = "_".join(datos[1:])
    valores = context.user_data["synth_params"]
    ranges = {
        "attack": (0.01, 0.5, 0.01),
        "decay": (0.01, 0.5, 0.01),
        "sustain": (0.3, 1.0, 0.05),
        "release": (0.05, 0.5, 0.01),
        "min_cutoff": (100, 3000, 100),
        "max_cutoff": (500, 6000, 100),
        "lfo_freq": (1, 15, 1),
        "lfo_depth": (0.0, 0.10, 0.01)
    }
    minv, maxv, step = ranges[param]
    val = valores[param]
    if accion == "up" and val + step <= maxv:
        val += step
    elif accion == "down" and val - step >= minv:
        val -= step
    valores[param] = round(val, 2) if isinstance(val, float) else val
    context.user_data["synth_params"] = valores
    valact = valores[param]
    kb = [
        [
            InlineKeyboardButton("➖", callback_data=f'down_{param}'),
            InlineKeyboardButton(f"Value: {valact:.2f}", callback_data='noop'),
            InlineKeyboardButton("➕", callback_data=f'up_{param}')
        ],
        [InlineKeyboardButton("⏎ Back to settings", callback_data='ajustes_menu')]
    ]
    await query.edit_message_text(
        f"🔧 Modify {param} (range: {minv}-{maxv}):",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def ver_valores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    params = context.user_data["synth_params"]
    msg = "🎛 **Current values:**\n\n"
    msg += f"**ADSR:**\n"
    msg += f"• Attack: {params['attack']:.2f}s\n"
    msg += f"• Decay: {params['decay']:.2f}s\n"
    msg += f"• Sustain: {params['sustain']:.2f}\n"
    msg += f"• Release: {params['release']:.2f}s\n\n"
    msg += f"**Filter:**\n"
    msg += f"• Min Cutoff: {params['min_cutoff']}Hz\n"
    msg += f"• Max Cutoff: {params['max_cutoff']}Hz\n\n"
    msg += f"**LFO:**\n"
    msg += f"• Frequency: {params['lfo_freq']}Hz\n"
    msg += f"• Depth: {params['lfo_depth']:.2f}"
    kb = [[InlineKeyboardButton("⏎ Back to settings", callback_data='ajustes_menu')]]
    await update.callback_query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='Markdown'
    )

async def navega_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_vals = context.user_data.get("synth_params", {
        "attack": ATTACK, "decay": DECAY, "sustain": SUSTAIN, "release": RELEASE,
        "min_cutoff": MIN_CUTOFF, "max_cutoff": MAX_CUTOFF, "lfo_freq": LFO_FREQ, "lfo_depth": LFO_DEPTH
    })
    context.user_data["synth_params"] = user_vals
    kb = [
        [
            InlineKeyboardButton("Attack", callback_data='set_attack'),
            InlineKeyboardButton("Decay", callback_data='set_decay'),
        ],
        [
            InlineKeyboardButton("Sustain", callback_data='set_sustain'),
            InlineKeyboardButton("Release", callback_data='set_release')
        ],
        [
            InlineKeyboardButton("Min Cutoff", callback_data='set_min_cutoff'),
            InlineKeyboardButton("Max Cutoff", callback_data='set_max_cutoff')
        ],
        [
            InlineKeyboardButton("LFO Freq", callback_data='set_lfo_freq'),
            InlineKeyboardButton("LFO Depth", callback_data='set_lfo_depth')
        ],
        [InlineKeyboardButton("Show current values", callback_data='see_vals')],
    ]
    await query.edit_message_text(
        "🎛 Adjust analog synth parameters (choose one to modify):",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---- AUDIO HANDLER ----
async def recibir_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        wave_type = context.user_data.get('wave_type', 'sine')
        user_params = context.user_data.get("synth_params", None)
        file = await update.message.voice.get_file()
        path_ogg = f"temp_audio_{update.effective_user.id}.ogg"
        await file.download_to_drive(path_ogg)
        path_wav = f"temp_audio_{update.effective_user.id}.wav"
        audio = AudioSegment.from_file(path_ogg, format="ogg")
        audio.export(path_wav, format="wav")
        path_sint = sintetizar_melodia_continua(path_wav, wave_type=wave_type, user_params=user_params)
        await update.message.reply_audio(audio=open(path_sint, "rb"))
        for f in [path_ogg, path_wav, path_sint]:
            try:
                os.remove(f)
            except:
                pass
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing audio: {e}")

# ---- START ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎹 Welcome to Whistle Synth 1.0!\n\n"
        "I am an analog-style synth bot that turns your whistle or humming into a synthesized melody.\n\n"
        "Available commands:\n"
        "• /waveform - Choose waveform type\n"
        "• /settings - Tweak ADSR, filter and LFO\n\n"
        "Then send me a voice message with your whistle/humming and enjoy the result."
    )

# ---- BOT SETUP ----
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("waveform", menu_ondas))
app.add_handler(CommandHandler("settings", ajustes_menu))

app.add_handler(CallbackQueryHandler(onda_seleccionada, pattern=r'^(sine|square|saw)$'))
app.add_handler(CallbackQueryHandler(ajustar_parametro, pattern=r'^set_.*'))
app.add_handler(CallbackQueryHandler(modificar_valor, pattern=r'^(up|down)_[a-z_]+$'))
app.add_handler(CallbackQueryHandler(ver_valores, pattern='^see_vals$'))
app.add_handler(CallbackQueryHandler(navega_menu, pattern='^ajustes_menu$'))

app.add_handler(MessageHandler(filters.VOICE, recibir_audio))

print("🎛 Whistle Synth 1.0 bot running...")
print("Commands: /start, /waveform, /settings")
app.run_polling()
