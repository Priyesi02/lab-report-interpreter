"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileCheck2, ArrowRight, Shield } from "lucide-react";
import { Logo, Card, PrimaryButton, GhostButton } from "../components/ui";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = (f: File | null) => {
    if (f && f.type === "application/pdf") {
      setFile(f);
    } else if (f) {
      alert("Please upload a standard medical report in PDF format.");
    }
  };

  const handleAnalyze = () => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      sessionStorage.setItem("lablens_pending_file_name", file.name);
      sessionStorage.setItem("lablens_pending_file_data", reader.result as string);
      router.push("/dashboard/analyzing");
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-canvas to-canvas-deep">
      <motion.header 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-7 sm:px-10"
      >
        <Logo />
        <GhostButton href="/">Back to home</GhostButton>
      </motion.header>

      <main className="mx-auto max-w-xl px-6 pb-24 pt-10 sm:px-10">
        <motion.div 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-10 text-center"
        >
          <h1 className="font-display text-[2.25rem] font-extrabold tracking-tightish text-ink leading-tight">
            Analyze clinical reports
          </h1>
          <p className="mx-auto mt-3 max-w-md text-[15px] text-muted leading-relaxed">
            Upload your medical record safely. Our encrypted analyzer itemizes diagnostics data instantly into accessible language.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <Card className="p-6 bg-white/80 backdrop-blur-md shadow-card">
            <motion.label
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                handleFile(e.dataTransfer.files?.[0] || null);
              }}
              whileHover={{ scale: 1.005 }}
              whileTap={{ scale: 0.995 }}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-[1.5px] border-dashed px-6 py-14 text-center transition-all duration-300 ${
                dragActive
                  ? "border-teal-500 bg-teal-50/40 shadow-inner"
                  : "border-line bg-canvas hover:border-teal-400 hover:bg-white"
              }`}
            >
              <motion.div 
                animate={{ scale: dragActive ? 1.1 : 1 }}
                className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-teal-50 text-teal-600 shadow-sm"
              >
                {file ? <FileCheck2 size={24} className="text-teal-500" /> : <UploadCloud size={24} />}
              </motion.div>
              
              <span className="text-[14.5px] font-bold text-ink max-w-[80%] truncate block">
                {file ? file.name : "Choose report file, or drop PDF here"}
              </span>
              <span className="mt-1 text-[12.5px] text-muted">
                Secure Document PDF up to 10MB
              </span>
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0] || null)}
              />
            </motion.label>

            <AnimatePresence mode="wait">
              {file && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mt-5"
                >
                  <PrimaryButton
                    onClick={handleAnalyze}
                    className="w-full group py-3.5"
                  >
                    Analyze Report 
                    <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-1" />
                  </PrimaryButton>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 flex items-center justify-center gap-2 text-[12.5px] text-faint bg-white/40 rounded-full py-2 px-4 border border-line/40 w-fit mx-auto"
        >
          <Shield size={13} className="text-teal-500" />
          <span>AES-256 data sanitization layer active</span>
        </motion.div>
      </main>
    </div>
  );
}