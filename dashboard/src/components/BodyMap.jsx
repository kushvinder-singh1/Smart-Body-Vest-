export default function BodyMap({ zones }) {
    const color = (v) =>
      v > 70 ? "red" : v > 30 ? "orange" : v > 0 ? "gold" : "#ddd";
  
    return (
      <div style={{ background: "white", padding: 20, borderRadius: 16, marginBottom: 20 }}>
        <h3>Heating Pads</h3>
  
        <div style={{ display: "flex", gap: 20, justifyContent: "center" }}>
          {Object.keys(zones).map((z) => (
            <div
              key={z}
              style={{
                width: 120,
                height: 120,
                borderRadius: 16,
                background: color(zones[z].intensity),
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#111",
                fontWeight: "bold"
              }}
            >
              {z.toUpperCase()}
            </div>
          ))}
        </div>
      </div>
    );
  }
  