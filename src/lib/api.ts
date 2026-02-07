// API Configuration for RuParked Frontend
// This connects the React frontend to the FastAPI backend

declare const __VITE_API_URL__: string | undefined;
const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_URL) || 'http://localhost:4000';


export const api = {
    baseUrl: API_BASE_URL,

    // Fetch wrapper with error handling
    async fetch(endpoint: string, options: RequestInit = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        return response.json();
    },

    // Navigation / Parking
    async getParkingLots() {
        return this.fetch('/navigation/commute/parking-lots');
    },

    async getMultiModalRoute(origin: { lat: number, lng: number }, destination: string) {
        return this.fetch(
            `/navigation/bus/multi-modal?origin_lat=${origin.lat}&origin_lng=${origin.lng}&destination_campus=${destination}`,
            { method: 'POST' }
        );
    },

    // Bus Routes
    async getBusRoutes() {
        return this.fetch('/navigation/bus/routes');
    },

    async getLiveBuses() {
        return this.fetch('/navigation/bus/live/buses');
    },

    async getBusInfo(routeId: string) {
        return this.fetch(`/navigation/bus/bus-info/${routeId}`);
    },

    // CV Integration - Parking Spots
    async getLiveParkingStatus(lotName?: string) {
        const query = lotName ? `?lot_name=${encodeURIComponent(lotName)}` : '';
        return this.fetch(`/navigation/bus/live/parking${query}`);
    },

    async getCVSpots(lotName: string) {
        return this.fetch(`/cv/spots/${encodeURIComponent(lotName)}`);
    },

    async getCVSummary() {
        return this.fetch('/cv/summary');
    },

    // Calendar
    async importCalendar(file: File, userId: string) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/student/calendar/import?user_id=${userId}`, {
            method: 'POST',
            body: formData,
        });

        return response.json();
    },

    async getCalendarEvents(userId: string, classesOnly = false) {
        return this.fetch(`/student/calendar/events?user_id=${userId}&classes_only=${classesOnly}`);
    },
};

export default api;
