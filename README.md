# Telegram Humming Synth Bot

Telegram bot that converts your humming into a synthesized melody using pitch detection (pYIN), digital oscillators, ADSR envelope, dynamic low‑pass filter, and LFO modulation.

## Features

- Voice message (humming / whistling) to synthesized audio.
- Waveform selection: sine, square, sawtooth.
- Analog-style controls:
  - Attack, Decay, Sustain, Release (ADSR)
  - Dynamic low‑pass filter (min/max cutoff)
  - LFO (frequency and depth) for pitch modulation.
- Interactive Telegram UI with inline buttons.

## Demo

<p align="center">
  <img src="img/1.jpg" alt="Step 1" width="220">
  <img src="img/2.jpg" alt="Step 2" width="220">
  <img src="img/3.jpg" alt="Step 3" width="220">
</p>
<p align="center"><em>Figure 1 – Main menu, waveform selection, and settings screen.</em></p>

<p align="center">
  <img src="img/4.jpg" alt="Step 4" width="220">
  <img src="img/5.jpg" alt="Step 5" width="220">
  <img src="img/6.jpg" alt="Step 6" width="220">
</p>
<p align="center"><em>Figure 2 – Main menu, waveform selection, and settings screen.</em></p>

## Requirements

- Python 3.10+  
- Libraries:
  - `python-telegram-bot`
  - `numpy`
  - `librosa`
  - `scipy`
  - `pydub`

Install:

```bash
pip install python-telegram-bot==21.0.1 numpy librosa scipy pydub
