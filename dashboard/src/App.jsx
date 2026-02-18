import { useEffect, useState } from "react";
import StatusCards from "./components/StatusCards";
import TempChart from "./components/TempChart";
import BodyMap from "./components/BodyMap";
import AlertsPanel from "./components/AlertsPanel";
import AIModelsPanel from "./components/AIModelsPanel";
import BatteryPanel from "./components/BatteryPanel";
import mockData from "./mockData.json";

function useMockStream() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      setData(mockData[i % mockData.length]);
      i++;
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return data;
}

function App() {
  const deviceData = useMockStream();

  if (!deviceData) return <div style={{ padding: 40 }}>Loading...</div>;

  return (
    <div style={{ padding: 24, background: "#f3f4f6", minHeight: "100vh" }}>
      <StatusCards data={deviceData} />
      <BatteryPanel battery={deviceData.battery} />
      <TempChart temp={deviceData.body_temp} />
      <BodyMap zones={deviceData.zones} />
      <AIModelsPanel ai={deviceData.ai_models} />
      <AlertsPanel alert={deviceData?.alerts?.latest} />
    </div>
  );
}

export default App;
