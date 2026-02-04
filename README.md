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
  <img src="img/1.jpg" alt="Bot main menu" width="300">
</p>

<p align="center">
  <img src="img/13.jpg" alt="Bot main menu" width="300">
</p>

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
