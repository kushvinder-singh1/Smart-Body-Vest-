export default function BatteryPanel({ battery }) {
    const color =
      battery > 60 ? "#22c55e" :
      battery > 30 ? "#f59e0b" :
      "#ef4444";
  
    return (
      <div style={{
        background: "white",
        padding: 20,
        borderRadius: 16,
        marginBottom: 20
      }}>
        <h3 style={{ marginBottom: 10 }}>Battery Status</h3>
  
        <div style={{
          height: 20,
          background: "#e5e7eb",
          borderRadius: 10,
          overflow: "hidden"
        }}>
          <div style={{
            width: `${battery}%`,
            height: "100%",
            background: color,
            transition: "width 0.5s ease"
          }} />
        </div>
  
        <div style={{ marginTop: 8, fontWeight: "bold" }}>
          {battery}%
        </div>
      </div>
    );
  }
  