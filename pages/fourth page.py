import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.title("🎉 Meme Page")

# Create meme image
width, height = 600, 400
img = Image.new("RGB", (width, height), color="white")
draw = ImageDraw.Draw(img)

# Big bold text

text_bottom = "ALL DEADLINES ARE ON MY BIRTHDAY 🎂"

# Load a default font
try:
    font = ImageFont.truetype("arial.ttf", 28)
except:
    font = ImageFont.load_default()

# Positioning
#draw.text((50, 100), text_top, fill="black", font=font)
draw.text((50, 200), text_bottom, fill="red", font=font)

st.image(img, caption="When deadlines and birthdays collide 💀")
