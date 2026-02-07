# RUParked

RUParked is a mobile application designed for Rutgers University students, with a focus on commuter convenience. It reduces logistical barriers -- primarily around parking -- to help students arrive on time, plan efficiently, and attend class reliably. The app combines real-time parking data, predictive forecasting, class schedule integration, and community-driven updates into a single platform built to reduce parking stress on campus.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Design Principles](#design-principles)
- [Educational Impact](#educational-impact)
- [Long-Term Vision](#long-term-vision)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Status](#status)
- [Contributing](#contributing)

---

## Overview

Commuter students frequently miss class due to stress caused by parking uncertainty or last-minute logistical challenges. RUParked addresses this by providing:

- Live campus parking maps with spot-level availability
- Predictive parking forecasts based on historical and real-time data
- Class schedule integration with nearest lot recommendations
- A social feed for student-driven parking updates
- A friends system for prioritized, trusted peer information

The goal is not to improve academic content directly but to make it easier for students to **show up consistently** -- removing the friction that keeps commuters from reaching the classroom.

---

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Dashboard** | Live parking map with clickable lots, detailed spot-level availability, and Smart Suggestions for optimal parking. | Implemented |
| **Time Travel** | Predictive parking forecasts starting at the current time, updating every 15 minutes up to 1 hour ahead. | Implemented |
| **Schedule Integration** | Connects class schedule to the nearest parking lot with availability forecasts tailored to upcoming sessions. | Implemented |
| **Social Feed** | Real-time updates from students, trending parking topics, likes, and comments. | Implemented |
| **Friends System** | Search and add friends, prioritize updates from trusted peers in the social feed. | Implemented |
| **Themes** | Universal clean interface or optional retro-inspired theme. Dark mode with Rutgers Red accents, JetBrains Mono font, fully toggleable. | Implemented |

---

## Design Principles

- Mobile-first, phone-native interface
- Clear, uncluttered layouts with information density optimized for commuters
- Navigation fully contained within the app frame
- Focused on readability, clarity, and low cognitive load
- Consistent typography and color accents for a professional appearance

---

## Educational Impact

RUParked improves access to education by reducing logistical friction that can prevent students from attending class. Parking uncertainty is one of the most common sources of daily stress for commuter students. By providing reliable parking information, predictive forecasts, and community-driven updates, the app helps students show up consistently and manage their day more effectively.

The project addresses a real barrier to academic participation -- not the quality of instruction, but the ability to physically reach the classroom on time.

---

## Long-Term Vision

RUParked is the foundation for a broader **Rutgers Navigator** platform. Potential future expansions include:

- Campus navigation and walking time integration
- Schedule-aware alerts and proactive planning tools
- Shuttle and bus route tracking
- Additional commuter-focused planning features

The long-term goal is to support students who struggle with time management by reducing stress and logistical barriers before problems occur.

---

## Screenshots

*Screenshots and demo media will be added here.*

- Dashboard view with Smart Suggestions and live parking map
- Time Travel forecast slider
- Class schedule integration with parking forecasts
- Social feed and friends system

---

## Installation

### Prerequisites

- Node.js (v18 or later)
- Python 3.10 or later
- npm or yarn

### Frontend Setup

```bash
git clone https://github.com/your-org/ruparked.git
cd ruparked
npm install
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the project root with the following keys. Replace placeholder values with your own credentials.

```env
AZURE_AD_B2C_TENANT_ID=your-tenant-id
AZURE_AD_B2C_CLIENT_ID=your-client-id
AZURE_AD_B2C_CLIENT_SECRET=your-client-secret
AZURE_COMMUNICATION_CONNECTION_STRING=your-communication-connection-string
AZURE_MAPS_SUBSCRIPTION_KEY=your-maps-subscription-key
AZURE_MAPS_CLIENT_ID=your-maps-client-id
AZURE_MAPS_BASE_URL=https://atlas.microsoft.com
AZURE_NOTIFICATION_HUB_CONNECTION_STRING=your-notification-hub-connection-string
AZURE_NOTIFICATION_HUB_NAME=your-notification-hub-name
AZURE_APP_INSIGHTS_CONNECTION_STRING=your-app-insights-connection-string
```

### Running the Application

Start the frontend development server:

```bash
npm run dev
```

Start the backend server:

```bash
cd backend
python main.py
```

---

## Status

Actively in development. Core features (dashboard, time travel, schedule integration, social feed, friends, themes) are implemented. Additional enhancements and testing are ongoing.

---

## Contributing

Contributions, feedback, and ideas are welcome.

To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature-name`)
5. Create a pull request

Please ensure that any contributions align with the existing code style and project direction.
