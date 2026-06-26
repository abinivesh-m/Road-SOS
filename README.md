# 🚨 NexusSOS – AI-Powered Emergency Response Platform

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-red)
![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Overview

**NexusSOS** is an AI-powered emergency response platform developed for the **IIT Madras CoERS / Ministry of Road Transport & Highways (MoRTH) Road Safety Hackathon**.

The platform combines **Artificial Intelligence**, **GPS-based emergency service discovery**, and **real-time emergency guidance** to help users quickly locate nearby emergency services and receive immediate assistance during critical situations.

---

## ✨ Features

### 🚑 Emergency Service Locator

* Nearby Hospitals
* Ambulances
* Police Stations
* Fire Stations
* Towing Services
* Vehicle Service Centers
* Live GPS & Manual City Search
* Distance-based nearest service ranking

---

### 🤖 AI Emergency Assistant

Powered by **Google Gemini 2.5 Flash**

The AI Assistant can:

* Detect emergency type
* Classify incident severity
* Extract location
* Recommend response units
* Estimate emergency response ETA
* Generate first-aid instructions
* Identify hazards & risks
* Explain AI confidence
* Generate offline emergency SMS
* Display incident timeline

---

### 🗺 Interactive Emergency Map

* Live emergency service markers
* OpenStreetMap integration
* Hospital
* Ambulance
* Police
* Fire
* Towing locations

---

### 📞 One-Tap Emergency Actions

For every emergency service:

* 📞 Call
* 🗺 Navigate
* 💬 Share via WhatsApp
* 📩 Share via SMS
* ⭐ Add to Favorites

---

### ⚙ Admin Panel

* Add new emergency services
* Search services
* CSV management
* Pending approvals
* Analytics dashboard

---

### 🌍 Multi-language Support

Supports multiple languages using a dedicated translation module.

---

### 📊 Analytics

Tracks:

* Emergency requests
* AI classifications
* Incident statistics
* Service usage

---

## 🛠 Tech Stack

* Python
* Streamlit
* Google Gemini 2.5 Flash API
* Pandas
* Geopy
* Streamlit Geolocation
* Folium
* Leaflet
* OpenStreetMap

---

## 📂 Project Structure

```text
RoadSOS/
│
├── app.py
├── ai_chat.py
├── ui.py
├── utils.py
├── translations.py
├── data.csv
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🚀 Installation

Clone the repository

```bash
git clone https://github.com/your-username/RoadSOS.git
```

Move into the project

```bash
cd RoadSOS
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a Streamlit secrets file

```text
.streamlit/secrets.toml
```

Add your Gemini API key

```toml
GEMINI_API_KEY="YOUR_API_KEY"
```

Run the application

```bash
streamlit run app.py
```

---

## 🔮 Future Scope

* Voice-based emergency reporting
* Automatic crash detection
* Live ambulance tracking
* IoT integration
* Offline emergency mode
* Push notifications
* Emergency contact synchronization
* Drone-assisted emergency response

---

## 🏛 Developed For

**IIT Madras CoERS**

**Ministry of Road Transport & Highways (MoRTH)**

Road Safety Hackathon

---

## ⚠ Disclaimer

NexusSOS is an AI-assisted emergency response support platform intended to assist users during emergencies. It is not a replacement for official emergency services. In life-threatening situations, immediately contact your local emergency helpline (India: **112**).

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 👨‍💻 Developer

**Abinivesh M**

B.E. Electronics and Communication Engineering

Sri Krishna College of Engineering and Technology (SKCET)

Tamil Nadu, India
