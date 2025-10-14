import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import CoursePage from './pages/CoursePage';
import LessonPlayerEnhanced from './pages/LessonPlayerEnhanced';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/course/:courseId" element={<CoursePage />} />
          <Route path="/lesson/:lessonId" element={<LessonPlayerEnhanced />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
