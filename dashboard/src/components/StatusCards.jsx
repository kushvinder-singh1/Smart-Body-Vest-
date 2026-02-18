export default function StatusCards({ data }) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 20 }}>
        <Card title="Body Temp" value={`${data.body_temp} °C`} />
        <Card title="Battery" value={`${data.battery}%`} />
        <Card title="Mode" value={data.mode} />
        <Card title="Device" value="Online" />
      </div>
    );
  }
  
  function Card({ title, value }) {
    return (
      <div style={{ background: "white", padding: 16, borderRadius: 16, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
        <div style={{ color: "#6b7280" }}>{title}</div>
        <div style={{ fontSize: 24, fontWeight: "bold" }}>{value}</div>
      </div>
    );
  }
  