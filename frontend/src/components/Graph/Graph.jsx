import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import {useState, useEffect} from 'react';
import styles from './Graph.module.css';



export default function Graph() {
    
  const [data, setData] = useState([
    { hour: 0, tokens: 0 },
    { hour: 2, tokens: 0 },
    { hour: 4, tokens: 0 },
    { hour: 6, tokens: 0 },
    { hour: 8, tokens: 0 },
    { hour: 10, tokens: 0 },
    { hour: 12, tokens: 0 },
    { hour: 14, tokens: 0 },
    { hour: 16, tokens: 0 },
    { hour: 18, tokens: 0 },
    { hour: 20, tokens: 0 },
    { hour: 22, tokens: 0 }
  ]);
    const [stats, setStats] = useState({
    input_tokens: 0,
    output_tokens: 0,
    peak_hours: 'N/A',
    daily_change: '0%'
  });


  
  const fetchChartData = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/token-usage');
      const jsonData = await response.json();
      setData(jsonData);
    } catch (error) {
      console.error('Error fetching chart data:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/graph-stats');
      const jsonData = await response.json();
      setStats(jsonData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };
    useEffect(() => {
        fetchChartData();
        fetchStats();
        const interval = setInterval(() => {
        fetchChartData();
        fetchStats();
        }, 30000);
        return () => clearInterval(interval);
    }, []);


    const formatXAxis = (decimalHour) => {
        const hours = Math.floor(decimalHour);
        const minutes = Math.round((decimalHour - hours) * 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    };


    return (
        <div className={styles.container}>
        <div className={styles.quickStats}>
          <h1>Daily Stats</h1>
          <ul>
            <li className={styles.stats}>Input Tokens: {stats.input_tokens.toLocaleString()}</li>
            <li className={styles.stats}>Output Tokens: {stats.output_tokens.toLocaleString()}</li>
            <li className={styles.stats}>Peak Hours: {stats.peak_hours}</li>
            <li className={styles.stats}>Daily Change: {stats.daily_change}</li>
          </ul>
        </div>
        <div className={styles.chart}>
            <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,100,120,0.2)" />
                <XAxis 
                  dataKey="hour"
                  tickFormatter={formatXAxis}
                  stroke="#9ca3af"
                  tick={{ fill: '#9ca3af' }}
                  type="number"
                  domain={[0, 24]}
                />

                <YAxis 
                stroke="#9ca3af"
                tick={{ fill: '#9ca3af' }}
                domain={[0, (dataMax) => Math.max(1000, dataMax)]}
                tickCount={6}
                />

                <Tooltip 
                contentStyle={{
                    backgroundColor: 'rgba(30, 30, 40, 0.95)',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    borderRadius: '8px',
                    color: '#e8e8e8'
                }}
                labelFormatter={formatXAxis}
                />
                
                <Legend wrapperStyle={{ color: '#e8e8e8' }} />
                <Line 
                type="monotone" 
                dataKey="tokens" 
                stroke="#6366f1" 
                strokeWidth={2.5}
                dot={{ fill: '#6366f1', r: 4 }}
                activeDot={{ r: 6 }}
                />
            </LineChart>
            </ResponsiveContainer>
        </div>
        </div>
    )
    }