export default function Card({
  className = "",
  padding = "p-6",
  hover = true,
  children,
  ...props
}) {
  return (
    <div
      className={`panel group ${hover ? "hover-lift" : ""} ${padding} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
