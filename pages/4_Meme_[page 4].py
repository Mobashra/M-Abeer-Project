import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.title("🎉 Meme Page")

# Create meme image
width, height = 600, 400
img = Image.new("RGB", (width, height), color="white")


st.image(img, caption="When deadlines and birthdays collide 💀")
