import { useState, useEffect } from 'react';
import styles from './StatCard.module.css'

function Card({title, value, color}) {
  return (

    <div className={styles.innerContainer}>
      <div className={styles.icon} style={{'--card-color': color}}></div>
      <div className={styles.title}>{title}</div>
      <div className={styles.value}>{value}</div>
    </div>

  );
}



export default function StatCard() {
  const [stats, setStats] = useState({
    daily_total: 0,
    monthly_total: 0,
    peak_day: 0,
    lifetime_total: 0
  });
  

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/stats');
      const jsonData = await response.json();
      setStats(jsonData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);
 
  
  return (
    <div className={styles.outerContainer}>
      <Card title="Daily Total" value={stats.daily_total.toLocaleString()} color='#3b82f6' />
      <Card title="Monthly Total" value={stats.monthly_total.toLocaleString()} color='#ef4444' />
      <Card title="Peak Day Record" value={stats.peak_day.toLocaleString()} color='#eab308' />
      <Card title="Lifetime Total" value={stats.lifetime_total.toLocaleString()} color='#22c55e' />
    </div>
  )


}