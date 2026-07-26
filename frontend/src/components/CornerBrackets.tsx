import React from "react";

/**
 * Wraps children with 4 small L-shaped corner marks (viewfinder-style),
 * inheriting color from `className`'s text color via currentColor.
 */
export default function CornerBrackets({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      <span className="absolute top-2 left-2 w-3 h-3 border-t border-l border-current pointer-events-none" />
      <span className="absolute top-2 right-2 w-3 h-3 border-t border-r border-current pointer-events-none" />
      <span className="absolute bottom-2 left-2 w-3 h-3 border-b border-l border-current pointer-events-none" />
      <span className="absolute bottom-2 right-2 w-3 h-3 border-b border-r border-current pointer-events-none" />
      {children}
    </div>
  );
}
