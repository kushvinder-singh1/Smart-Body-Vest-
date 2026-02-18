export default function AIModelsPanel({ ai }) {
    if (!ai) return null;
  
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 20 }}>
        <Card title="LSTM Temp" value={`${ai.lstm.predicted_temp_15min} °C`} />
        <Card title="LSTM Latency" value={`${ai.lstm.latency_ms} ms`} />
        <Card title="DNN Latency" value={`${ai.dnn.latency_ms} ms`} />
      </div>
    );
  }
  
  function Card({ title, value }) {
    return (
      <div style={{ background: "white", padding: 16, borderRadius: 16 }}>
        <div style={{ color: "#6b7280" }}>{title}</div>
        <div style={{ fontSize: 22, fontWeight: "bold" }}>{value}</div>
      </div>
    );
  }
  