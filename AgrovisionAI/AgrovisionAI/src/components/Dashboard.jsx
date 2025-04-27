
import { useState } from 'react';
import WeatherWidget from './WeatherWidget';
import LeafAnalyzer from './LeafAnalyzer';

function Dashboard({ user, weatherData }) {
  const [activeTab, setActiveTab] = useState('weather');

  return (
    <div className="dashboard">
      <nav className="dashboard-nav">
        <button onClick={() => setActiveTab('weather')}>Weather</button>
        <button onClick={() => setActiveTab('analyzer')}>Leaf Analyzer</button>
      </nav>
      
      <div className="dashboard-content">
        {activeTab === 'weather' && <WeatherWidget data={weatherData} />}
        {activeTab === 'analyzer' && <LeafAnalyzer />}
      </div>
    </div>
  );
}

export default Dashboard;
