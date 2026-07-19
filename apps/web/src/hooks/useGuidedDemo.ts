"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Incident } from "@/lib/api";


export function useGuidedDemo({
  incident,
  reportCount,
  startDemoSignal,
}: {
  incident: Incident | null;
  reportCount: number;
  startDemoSignal: number;
}) {
  const [demoMode, setDemoMode] = useState(false);
  const [demoStep, setDemoStep] = useState(1);
  const [containmentReviewOpen, setContainmentReviewOpen] = useState(false);
  const handledDemoSignal = useRef(0);

  const startGuidedDemo = useCallback(() => {
    setDemoMode(true);
    setContainmentReviewOpen(false);
    if (incident?.reassessment || incident?.proposedRevision) setDemoStep(6);
    else if (incident?.tasks.length) setDemoStep(5);
    else if (incident) setDemoStep(3);
    else if (reportCount >= 3) setDemoStep(2);
    else setDemoStep(1);
    window.requestAnimationFrame(() => {
      const workspace = document.getElementById("incidents");
      if (typeof workspace?.scrollIntoView === "function") {
        workspace.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }, [incident, reportCount]);

  useEffect(() => {
    if (startDemoSignal <= handledDemoSignal.current) return;
    handledDemoSignal.current = startDemoSignal;
    startGuidedDemo();
  }, [startDemoSignal, startGuidedDemo]);

  return {
    containmentReviewOpen,
    demoMode,
    demoStep,
    setContainmentReviewOpen,
    setDemoMode,
    setDemoStep,
  };
}
