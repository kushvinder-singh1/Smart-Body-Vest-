export default function AlertsPanel({ alert }) {
    if (!alert) return null;
  
    return (
      <div style={{ background: "#fee2e2", padding: 16, borderRadius: 12 }}>
        ⚠️ {alert}
      </div>
    );
  }
  