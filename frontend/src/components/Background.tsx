import { useEffect, useRef } from "react";

export function Background() {
  const scene = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let frame = 0;
    let targetX = 0; let targetY = 0; let currentX = 0; let currentY = 0;
    const render = () => {
      currentX += (targetX - currentX) * .075;
      currentY += (targetY - currentY) * .075;
      scene.current?.style.setProperty("--px", currentX.toFixed(3));
      scene.current?.style.setProperty("--py", currentY.toFixed(3));
      frame = requestAnimationFrame(render);
    };
    const move = (event: PointerEvent) => {
      targetX = (event.clientX / window.innerWidth - .5) * 2;
      targetY = (event.clientY / window.innerHeight - .5) * 2;
    };
    frame = requestAnimationFrame(render);
    window.addEventListener("pointermove", move, { passive: true });
    return () => { cancelAnimationFrame(frame); window.removeEventListener("pointermove", move); };
  }, []);

  return <div ref={scene} aria-hidden="true" className="scene">
    <div className="noise" />
    <div className="grid" />
    <div className="dot-field" />
    <div className="contour-lines" />
    <div className="scanlines" />
    <div className="orb orb-one" />
    <div className="orb orb-two" />
    <div className="orb orb-three" />
    <div className="light-beam beam-one" />
    <div className="light-beam beam-two" />
    <div className="pointer-ring ring-one" />
    <div className="pointer-ring ring-two" />
    <div className="pointer-spark spark-one" />
    <div className="pointer-spark spark-two" />
    <div className="cursor-glow" />
    <div className="particles">{Array.from({ length: 30 }, (_, index) => <i key={index} />)}</div>
  </div>;
}
