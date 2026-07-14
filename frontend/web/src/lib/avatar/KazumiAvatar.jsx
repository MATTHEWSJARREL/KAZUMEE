export default function KazumiAvatar({ size = 36, className = "" }) {
  return (
    <img
      src="/zumi.png"
      alt="Zumi"
      width={size}
      height={size}
      className={className}
      style={{ borderRadius: "50%", objectFit: "cover" }}
      onError={e => { e.currentTarget.style.display = "none"; }}
    />
  );
}