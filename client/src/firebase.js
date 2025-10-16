import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyCnFGCav-H7jVtZeVd8aL65C_P-jgN49Y4",
  authDomain: "streaming-service-b8c08.firebaseapp.com",
  projectId: "streaming-service-b8c08",
  storageBucket: "streaming-service-b8c08.firebasestorage.app",
  messagingSenderId: "502088236431",
  appId: "1:502088236431:web:8209be1c6d392492cadffa",
  measurementId: "G-M3MTEXC55L"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;
