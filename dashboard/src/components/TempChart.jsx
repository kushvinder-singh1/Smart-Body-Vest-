import { Line } from "react-chartjs-2";
import { Chart as ChartJS, LineElement, PointElement, LinearScale, CategoryScale } from "chart.js";
import { useEffect, useState } from "react";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale);

export default function TempChart({ temp }) {
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [{ label: "Body Temp", data: [] }]
  });

  useEffect(() => {
    setChartData(prev => ({
      labels: [...prev.labels, new Date().toLocaleTimeString()].slice(-30),
      datasets: [{
        ...prev.datasets[0],
        data: [...prev.datasets[0].data, temp].slice(-30)
      }]
    }));
  }, [temp]);

  return (
    <div style={{ background: "white", padding: 20, borderRadius: 16, marginBottom: 20 }}>
      <Line data={chartData} />
    </div>
  );
}
