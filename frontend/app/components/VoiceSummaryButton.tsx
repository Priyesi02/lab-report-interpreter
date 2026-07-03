'use client';

import React, { useState, useEffect } from 'react';
import { Volume2, Square, Loader2 } from 'lucide-react';

interface VoiceButtonProps {
  email: string;
  reportId: string;
}

export const VoiceSummaryButton: React.FC<VoiceButtonProps> = ({ email, reportId }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [supported, setSupported] = useState(true);

  useEffect(() => {
    if (typeof window !== 'undefined' && !window.speechSynthesis) {
      setSupported(false);
    }
  }, []);

  const handleSpeak = async () => {
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }

    try {
      setIsLoading(true);
      const targetUrl = `http://127.0.0.1:8000/api/patient/report/text-summary?email=${encodeURIComponent(email)}&report_id=${reportId}`;
      const response = await fetch(targetUrl);
      const data = await response.json();

      if (!response.ok || !data.summary_text) {
        throw new Error("Failed to compile script data mapping paths");
      }

      setIsLoading(false);

      const utterance = new SpeechSynthesisUtterance(data.summary_text);
      const voices = window.speechSynthesis.getVoices();
      const premiumVoice = voices.find(voice => 
        voice.name.includes("Google US English") || 
        voice.name.includes("Samantha") || 
        voice.lang === "en-US"
      );

      if (premiumVoice) utterance.voice = premiumVoice;
      utterance.rate = 0.93;  
      utterance.pitch = 1.02; 

      utterance.onstart = () => setIsPlaying(true);
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => {
        setIsPlaying(false);
      };

      window.speechSynthesis.speak(utterance);

    } catch (error) {
      console.error("Audio engine failed:", error);
      setIsLoading(false);
      setIsPlaying(false);
    }
  };

  if (!supported) return null;

  return (
    <button
      onClick={handleSpeak}
      disabled={isLoading}
      className={`w-full flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-[13px] font-bold font-display tracking-tight transition-all outline-none ${
        isPlaying 
          ? 'bg-red-50 text-red-600 border-red-200 animate-pulse' 
          : 'bg-white border-teal-500/20 text-teal-700 hover:bg-teal-50 hover:border-teal-500/40'
      }`}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : isPlaying ? (
        <Square className="w-4 h-4 fill-current" />
      ) : (
        <Volume2 className="w-4 h-4" />
      )}
      
      {isLoading ? "Compiling Script..." : isPlaying ? "Stop Listening" : "Listen to AI Summary"}
    </button>
  );
};