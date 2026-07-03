"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { VoiceSummaryButton } from '../../components/VoiceSummaryButton';
import {
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    BarChart,
    Bar,
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
} from "recharts";
import {
    RotateCcw,
    Activity,
    AlertCircle,
    Stethoscope,
    HelpCircle,
    MapPin,
    ClipboardList,
    Clock,
    TrendingUp,
} from "lucide-react";
import { Logo, Avatar, PillBadge, Card, GhostButton } from "../../components/ui";
import { getAuthenticatedUser } from '@/utils/aws-cognito';

type AbnormalValue = {
    name: string;
    value: string | number;
    unit?: string;
    status: string;
};

type NearbyDoctor = {
    name: string;
    address: string;
};

type AnalysisResult = {
    id?: string;
    file_name?: string;
    analyzed_at?: string;
    patient_name?: string;
    report_date?: string;
    total_tests?: number;
    normal_count?: number;
    abnormal_count?: number;
    status?: string;
    health_score?: number;
    abnormal_values?: AbnormalValue[];
    specialist?: {
        primary_specialist?: string;
        urgency?: string;
        reason?: string;
    };
    questions?: { questions?: string[] };
    nearby_doctors?: NearbyDoctor[];
};

const statusTone: Record<string, "danger" | "warning" | "critical" | "success"> = {
    HIGH: "danger",
    LOW: "warning",
    CRITICAL: "critical",
    NORMAL: "success",
};

export default function ResultsPage() {
    const router = useRouter();
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [history, setHistory] = useState<AnalysisResult[]>([]);
    const [loaded, setLoaded] = useState(false);
    const [activeTab, setActiveTab] = useState<"analysis" | "questions" | "doctors" | "history">("analysis");

    useEffect(() => {
        async function loadHistory() {
            const auth = await getAuthenticatedUser();
            if (!auth.success || !auth.email) {
                setHistory([]);
                setResult(null);
                setLoaded(true);
                return;
            }

            try {
                const res = await fetch(`http://127.0.0.1:8000/api/patient/history?email=${encodeURIComponent(auth.email)}`);
                if (!res.ok) throw new Error(`history fetch failed ${res.status}`);

                const data = await res.json();
                const records: AnalysisResult[] = Array.isArray(data.history) ? (data.history as AnalysisResult[]) : [];
                setHistory(records);

                const url = new URL(window.location.href);
                const requestedId = url.searchParams.get("reportId");
                const selected = requestedId ? records.find((r: AnalysisResult) => r.id === requestedId) : records[0];

                if (selected) {
                    setResult(selected);
                } else if (records.length > 0) {
                    setResult(records[0]);
                } else {
                    setResult(null);
                }
            } catch (err) {
                console.error("Unable to load history:", err);
                setHistory([]);
                setResult(null);
            } finally {
                setLoaded(true);
            }
        }

        loadHistory();
    }, [router]);

    if (!loaded) return null;

    if (!result) {
        return (
            <div className="min-h-screen bg-gradient-to-b from-canvas to-canvas-deep pb-24 selection:bg-teal-50">
                <div className="mx-auto max-w-[1280px] px-6 py-10 sm:px-10">
                    <div className="mb-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-line pb-6">
                        <Logo size={44} />
                        <button
                            onClick={() => router.push('/dashboard')}
                            className="rounded-full border border-teal-500/20 bg-white/80 px-5 py-3 text-[13px] font-medium text-teal-700 transition hover:bg-teal-50"
                        >
                            Add new report
                        </button>
                    </div>

                    <div className="rounded-3xl border border-line bg-white/80 p-10 text-center shadow-card">
                        <h1 className="text-[24px] font-bold text-ink mb-3">No saved reports yet</h1>
                        <p className="text-[15px] text-muted mb-8">Once you upload your first clinical report, your latest result will appear here along with the report history.</p>
                        <button
                            onClick={() => router.push('/dashboard')}
                            className="inline-flex items-center justify-center rounded-full bg-teal-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-600"
                        >
                            Upload first report
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const initials = (result.patient_name || "P").trim().charAt(0).toUpperCase();
    const normalVal = result.normal_count || 0;
    const abnormalVal = result.abnormal_count || 0;
    const healthScore = result.health_score ?? (result.total_tests ? Math.round((normalVal / result.total_tests) * 100) : 75);

    const testDistributionData = [
        { name: "Normal Levels", value: normalVal, color: "#10b981" },
        { name: "Out of Range", value: abnormalVal, color: "#ef4444" },
    ];

    const markerBreakdownData = result.abnormal_values?.map(item => ({
        name: item.name.length > 14 ? item.name.substring(0, 12) + ".." : item.name,
        Value: parseFloat(String(item.value)) || 40,
    })).slice(0, 5) || [];

    // Map and reverse timeline tracking data so chronological time reads from Left -> Right
    const timelineData = [...history]
        .map(item => {
            const normal = item.normal_count || 0;
            const total = item.total_tests || 1;
            const computedScore = item.health_score ?? Math.round((normal / total) * 100);
            return {
                date: item.report_date || "Unknown Date",
                "Health Score": computedScore,
            };
        })
        .reverse();

    return (
        <div className="min-h-screen bg-gradient-to-b from-canvas to-canvas-deep pb-24 selection:bg-teal-50">
            <div className="mx-auto max-w-[1280px] px-6 py-10 sm:px-10">

                {/* TOP BAR */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-line pb-6"
                >
                    <Logo size={44} />
                    <div className="flex flex-wrap items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                        <span className="text-[13.5px] font-medium font-display text-muted">
                            {result.patient_name || "Guest User"} · {result.report_date || "Recent Report"}
                        </span>
                        <GhostButton
                            onClick={() => router.push("/dashboard")}
                            className="group border-teal-500/20 hover:border-teal-500/40 text-[13px] font-medium"
                        >
                            <RotateCcw size={13} className="transition-transform duration-500 group-hover:rotate-180" /> Add new report
                        </GhostButton>
                    </div>
                </motion.div>

                {/* MINIMALIST LINE NAVIGATION TABS */}
                <div className="flex items-center gap-8 mb-10 border-b border-line/60 overflow-x-auto scrollbar-none w-full">
                    {[
                        { id: "analysis", label: "My Results", icon: ClipboardList },
                        { id: "questions", label: "Doctor Prep Guide", icon: HelpCircle },
                        { id: "doctors", label: "Doctors Near Me", icon: MapPin },
                        { id: "history", label: "Report History", icon: Clock }
                    ].map((tab) => {
                        const IsActive = activeTab === tab.id;
                        const TabIcon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={`relative flex items-center gap-2 pb-4 text-[14.5px] font-bold font-display tracking-tight transition-colors whitespace-nowrap outline-none ${IsActive ? "text-teal-600" : "text-muted hover:text-ink"
                                    }`}
                            >
                                <TabIcon size={16} strokeWidth={IsActive ? 2.5 : 2} />
                                {tab.label}
                                {IsActive && (
                                    <motion.div
                                        layoutId="activeTabIndicator"
                                        className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-teal-400 to-teal-500 rounded-full"
                                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                                    />
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* WORKSPACE SIDEBAR + VIEWER LAYOUT */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">

                    {/* LEFT SIDEBAR */}
                    <div className="space-y-6 lg:col-span-1">

                        {/* OVERVIEW SUMMARY CARD */}
                        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
                            <Card className="p-6 bg-white shadow-card">
                                <div className="flex items-center gap-4">
                                    <Avatar label={initials} size={50} />
                                    <div>
                                        <h2 className="text-[17px] font-extrabold font-display text-ink leading-tight">
                                            {result.patient_name || "Patient Record"}
                                        </h2>
                                        <p className="text-[12.5px] font-medium text-muted mt-0.5">
                                            Report date: {result.report_date || "Not specified"}
                                        </p>
                                    </div>
                                </div>
                                <div className="mt-4">
                                    <VoiceSummaryButton
                                        email={history[0] ? history[0].patient_name || "test@example.com" : "test@example.com"}
                                        reportId={result.id || "default"}
                                    />
                                </div>
                                <div className="my-5 h-px bg-line" />
                                <div className="grid grid-cols-3 gap-2 text-center">
                                    <div className="bg-canvas p-2.5 rounded-xl border border-line/40">
                                        <span className="block text-[11px] font-bold font-display uppercase tracking-wider text-muted">Total Tests</span>
                                        <span className="text-[19px] font-extrabold text-ink">{result.total_tests ?? "—"}</span>
                                    </div>
                                    <div className="bg-status-success-bg/40 p-2.5 rounded-xl border border-status-success/10">
                                        <span className="block text-[11px] font-bold font-display uppercase tracking-wider text-status-success">Normal</span>
                                        <span className="text-[19px] font-extrabold text-status-success">{result.normal_count ?? "—"}</span>
                                    </div>
                                    <div className="bg-status-danger-bg/40 p-2.5 rounded-xl border border-status-danger/10">
                                        <span className="block text-[11px] font-bold font-display uppercase tracking-wider text-status-danger">Attention</span>
                                        <span className="text-[19px] font-extrabold text-status-danger">{result.abnormal_count ?? "—"}</span>
                                    </div>
                                </div>
                            </Card>
                        </motion.div>

                        {/* OVERALL HEALTH SCORE - GLASSMORPHISM CARD */}
                        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                            <div className="p-6 rounded-2xl border border-white/70 bg-white/40 backdrop-blur-xl relative overflow-hidden text-center shadow-card">
                                <h3 className="text-[14px] font-bold font-display tracking-tightish text-ink mb-1">Your Lab Health Score</h3>
                                <p className="text-[12px] text-muted max-w-[85%] mx-auto mb-4">A simple summary percentage based on how many parameters are looking healthy.</p>

                                <div className="relative mx-auto w-36 h-36 flex items-center justify-center">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={[{ value: healthScore }, { value: 100 - healthScore }]}
                                                innerRadius={52}
                                                outerRadius={62}
                                                startAngle={90}
                                                endAngle={-270}
                                                dataKey="value"
                                                stroke="none"
                                            >
                                                <Cell fill="url(#tealGradient)" />
                                                <Cell fill="rgba(15, 23, 42, 0.05)" />
                                            </Pie>
                                            <defs>
                                                <linearGradient id="tealGradient" x1="0" y1="0" x2="1" y2="1">
                                                    <stop offset="0%" stopColor="#2dd4bf" />
                                                    <stop offset="100%" stopColor="#0891b2" />
                                                </linearGradient>
                                            </defs>
                                        </PieChart>
                                    </ResponsiveContainer>

                                    <div className="absolute flex flex-col items-center justify-center">
                                        <span className="text-[34px] font-black tracking-tighter text-ink leading-none">{healthScore}%</span>
                                        <span className="text-[11px] font-bold font-display text-teal-600 tracking-wide uppercase mt-0.5">Healthy</span>
                                    </div>
                                </div>

                                <div className="mt-4 inline-block px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-[12px] font-bold font-display text-teal-700">
                                    Overall Status: <span className="uppercase text-ink">{result.status ?? "STABLE"}</span>
                                </div>
                            </div>
                        </motion.div>

                        {/* TEST BALANCE RATIO */}
                        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                            <div className="p-5 rounded-2xl border border-white/70 bg-white/40 backdrop-blur-xl shadow-card">
                                <h4 className="text-[13.5px] font-bold font-display text-ink mb-3">Health Balance</h4>
                                <div className="h-40 w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={testDistributionData}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={35}
                                                outerRadius={50}
                                                paddingAngle={5}
                                                dataKey="value"
                                                stroke="none"
                                            >
                                                {testDistributionData.map((entry, idx) => (
                                                    <Cell key={`cell-${idx}`} fill={entry.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip contentStyle={{ background: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0", fontSize: "12px" }} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="flex justify-center gap-6 text-[12px] font-bold font-display text-muted">
                                    <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-500" />Normal ({normalVal})</span>
                                    <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-red-500" />Out of Range ({abnormalVal})</span>
                                </div>
                            </div>
                        </motion.div>

                        {/* RECOMMENDED MEDICAL STREAM */}
                        {result.specialist && (
                            <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                                <Card className="p-6 bg-white shadow-card border-l-[4px] border-l-teal-400">
                                    <div className="flex items-start gap-4">
                                        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-600 shadow-sm">
                                            <Stethoscope size={20} />
                                        </div>
                                        <div className="flex-1">
                                            <span className="text-[11px] font-bold font-display uppercase tracking-wider text-muted block">
                                                Suggested Doctor Specialty
                                            </span>
                                            <div className="text-[17px] font-extrabold font-display text-ink mt-0.5 leading-tight">
                                                {result.specialist.primary_specialist || "General Physician"}
                                            </div>
                                        </div>
                                    </div>
                                    {result.specialist.reason && (
                                        <div className="mt-4 rounded-xl bg-canvas/60 p-3.5 border border-line/60 text-[13.5px] leading-relaxed text-muted">
                                            <span className="font-bold text-ink block mb-0.5">Why this matches:</span>
                                            {result.specialist.reason}
                                        </div>
                                    )}
                                </Card>
                            </motion.div>
                        )}
                    </div>

                    {/* RIGHT VIEWPORT CONTENT CHANGER AREA */}
                    <div className="lg:col-span-2">
                        <AnimatePresence mode="wait">

                            {/* TAB 1: MAIN BIOMARKER METRICS ANALYSIS */}
                            {activeTab === "analysis" && (
                                <motion.div
                                    key="analysis"
                                    initial={{ opacity: 0, x: 10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -10 }}
                                    transition={{ duration: 0.2 }}
                                    className="space-y-6"
                                >
                                    {/* CONDITIONAL COMPARISON TIMELINE (Only renders if > 1 reports exist) */}
                                    {history.length > 1 && (
                                        <div className="p-6 rounded-2xl border border-white/70 bg-white/40 backdrop-blur-xl shadow-card">
                                            <h3 className="text-[14.5px] font-bold font-display text-ink mb-1 flex items-center gap-2">
                                                <TrendingUp size={16} className="text-teal-500" /> Medical Trends Timeline
                                            </h3>
                                            <p className="text-[12px] text-muted mb-6">Tracking changes in your aggregate scores over chronological history.</p>
                                            <div className="h-48 w-full">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={timelineData} margin={{ top: 10, right: 20, left: -25, bottom: 0 }}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.04)" vertical={false} />
                                                        <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} padding={{ left: 10, right: 10 }} />
                                                        <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                                                        <Tooltip contentStyle={{ background: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0", fontSize: "12px" }} />
                                                        <Line
                                                            type="monotone"
                                                            dataKey="Health Score"
                                                            stroke="url(#lineGradient)"
                                                            strokeWidth={3}
                                                            dot={{ r: 4, stroke: "#2dd4bf", strokeWidth: 2, fill: "#fff" }}
                                                            activeDot={{ r: 6 }}
                                                        />
                                                        <defs>
                                                            <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                                                                <stop offset="0%" stopColor="#2dd4bf" />
                                                                <stop offset="100%" stopColor="#06b6d4" />
                                                            </linearGradient>
                                                        </defs>
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    )}

                                    {markerBreakdownData.length > 0 && (
                                        <div className="p-6 rounded-2xl border border-white/70 bg-white/40 backdrop-blur-xl shadow-card">
                                            <h3 className="text-[14.5px] font-bold font-display text-ink mb-4 flex items-center gap-2">
                                                <Activity size={16} className="text-teal-500" /> Values Requiring Check
                                            </h3>
                                            <div className="h-48 w-full">
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <BarChart data={markerBreakdownData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                                        <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                                        <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                                                        <Tooltip contentStyle={{ borderRadius: '8px', fontSize: '12px' }} />
                                                        <Bar dataKey="Value" radius={[6, 6, 0, 0]} maxBarSize={32}>
                                                            {markerBreakdownData.map((entry, index) => (
                                                                <Cell key={`cell-${index}`} fill={index % 2 === 0 ? "#06b6d4" : "#2dd4bf"} />
                                                            ))}
                                                        </Bar>
                                                    </BarChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    )}

                                    {result.abnormal_values && result.abnormal_values.length > 0 ? (
                                        <Card className="p-6 bg-white shadow-card">
                                            <div className="mb-4 flex items-center gap-2.5">
                                                <AlertCircle size={18} className="text-status-danger" />
                                                <h3 className="text-[16px] font-extrabold font-display text-ink">
                                                    Flags Found in Report
                                                </h3>
                                            </div>
                                            <div className="space-y-3">
                                                {result.abnormal_values.map((item, i) => {
                                                    const tone = statusTone[item.status.toUpperCase()] || "success";
                                                    return (
                                                        <div
                                                            key={i}
                                                            className={`rounded-xl border border-line border-l-[4px] p-4 bg-canvas/30 ${tone === "danger" ? "border-l-status-danger bg-status-danger-bg/5" :
                                                                tone === "warning" ? "border-l-status-warning bg-status-warning-bg/5" :
                                                                    tone === "critical" ? "border-l-status-critical bg-status-critical-bg/5" :
                                                                        "border-l-status-success"
                                                                }`}
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <p className="font-bold font-display text-ink text-[14.5px]">
                                                                    {item.name}
                                                                </p>
                                                                <PillBadge tone={tone}>{item.status === "HIGH" ? "High Value" : item.status === "LOW" ? "Low Value" : item.status}</PillBadge>
                                                            </div>
                                                            <p className="mt-1.5 text-[13.5px] font-bold text-ink bg-white/70 px-2.5 py-1 rounded-md w-fit border border-line/40">
                                                                Your Value: <span className="text-teal-600 font-black">{item.value}</span> {item.unit || ""}
                                                            </p>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </Card>
                                    ) : (
                                        <Card className="p-10 text-center bg-white shadow-card">
                                            <p className="text-[15px] font-medium text-muted">No high or low flags detected. All markers look standard!</p>
                                        </Card>
                                    )}
                                </motion.div>
                            )}

                            {/* TAB 2: CONSULTATION PREPARATION GUIDE */}
                            {activeTab === "questions" && (
                                <motion.div
                                    key="questions"
                                    initial={{ opacity: 0, x: 10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -10 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <Card className="p-6 bg-white shadow-card">
                                        <div className="mb-4 flex items-center gap-2.5">
                                            <HelpCircle size={18} className="text-teal-500" />
                                            <h3 className="text-[16px] font-extrabold font-display text-ink">
                                                Questions to Ask Your Doctor
                                            </h3>
                                        </div>
                                        <p className="text-[13.5px] text-muted mb-5 leading-relaxed">
                                            We recommend bringing these simple points up during your next session to better understand your numbers.
                                        </p>
                                        {result.questions?.questions && result.questions.questions.length > 0 ? (
                                            <ul className="space-y-3">
                                                {result.questions.questions.map((q, i) => (
                                                    <li key={i} className="flex items-start gap-3 text-[14px] bg-canvas/30 p-3.5 rounded-xl border border-line/40">
                                                        <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-teal-400" />
                                                        <span className="leading-relaxed font-medium text-ink">{q}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <ul className="space-y-3">
                                                <li className="flex items-start gap-3 text-[14px] bg-canvas/30 p-3.5 rounded-xl border border-line/40">
                                                    <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-teal-400" />
                                                    <span className="leading-relaxed font-medium text-ink">Are there any lifestyle or food modifications you suggest based on these ranges?</span>
                                                </li>
                                                <li className="flex items-start gap-3 text-[14px] bg-canvas/30 p-3.5 rounded-xl border border-line/40">
                                                    <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-teal-400" />
                                                    <span className="leading-relaxed font-medium text-ink">When should I retake this test to see if the markers have improved?</span>
                                                </li>
                                            </ul>
                                        )}
                                    </Card>
                                </motion.div>
                            )}

                            {/* TAB 3: REPORT HISTORY */}
                            {activeTab === "history" && (
                                <motion.div
                                    key="history"
                                    initial={{ opacity: 0, x: 10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -10 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <Card className="p-6 bg-white shadow-card">
                                        <div className="mb-4 flex items-center gap-2.5">
                                            <Clock size={18} className="text-teal-500" />
                                            <h3 className="text-[16px] font-extrabold font-display text-ink">
                                                Report history
                                            </h3>
                                        </div>
                                        <p className="text-[13.5px] text-muted mb-5 leading-relaxed">
                                            Select any past report to revisit that analysis and keep your medical timeline accessible.
                                        </p>

                                        {history.length > 0 ? (
                                            <div className="space-y-3">
                                                {history.map((item, index) => {
                                                    const reportId = item.id ?? '';
                                                    return (
                                                        <button
                                                            key={item.id || index}
                                                            onClick={() => router.push(`/dashboard/results?reportId=${encodeURIComponent(reportId)}`)}
                                                            className={`w-full text-left rounded-3xl border px-5 py-4 transition hover:border-teal-300/70 hover:bg-white ${result?.id === item.id ? "border-teal-400 bg-teal-50/40" : "border-line"}`}
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <div>
                                                                    <p className="font-bold text-ink text-sm">{item.file_name || "Lab Report"}</p>
                                                                    <p className="text-xs text-muted mt-0.5">{item.report_date || "Unknown Date"}</p>
                                                                </div>
                                                                <span className="text-sm font-extrabold text-teal-600">{item.health_score ?? 75}%</span>
                                                            </div>
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        ) : (
                                            <p className="text-[14px] text-muted text-center py-6">No historical records available.</p>
                                        )}
                                    </Card>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
}