"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { 
  Users, 
  FileCheck, 
  AlertCircle, 
  ChevronRight, 
  ArrowUpRight,
  Search,
  LayoutDashboard,
  Settings,
  Bell
} from "lucide-react"

const API_BASE = "http://localhost:8000"

interface Case {
  phone: string
  name: string
  state: string
  compliance_score: string | number
  identity_confidence: string | number
  total_entitlement: number
  status: string
  step: number
}

export default function Dashboard() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)

  const fetchDashboardData = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard`)
      if (res.ok) {
        const data = await res.json()
        setCases(data.cases || [])
      }
    } catch (err) {
      console.error("Dashboard fetch error:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex h-screen bg-[#f8f9fa] text-zinc-900 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-zinc-200 flex flex-col">
        <div className="p-6 flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold">H</div>
          <span className="font-bold text-xl tracking-tight">Haqdaar Admin</span>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-1">
          <SidebarLink icon={<LayoutDashboard size={20}/>} label="Overview" active />
          <SidebarLink icon={<Users size={20}/>} label="Active Cases" />
          <SidebarLink icon={<AlertCircle size={20}/>} label="Disputes" />
          <SidebarLink icon={<Settings size={20}/>} label="Settings" />
        </nav>

        <div className="p-6 border-t border-zinc-100">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-500 font-bold text-xs uppercase">VN</div>
             <div>
                <p className="text-xs font-bold uppercase tracking-wider text-zinc-400">Moderator</p>
                <p className="text-sm font-semibold">Vaibhav N.</p>
             </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-zinc-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4 flex-1">
             <div className="relative w-96">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={18} />
                <input 
                  type="text" 
                  placeholder="Search beneficiaries or claim IDs..." 
                  className="w-full bg-zinc-100 border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none"
                />
             </div>
          </div>
          <div className="flex items-center gap-4">
             <button className="p-2 hover:bg-zinc-100 rounded-full transition-colors relative">
                <Bell size={20} className="text-zinc-600" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
             </button>
             <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-all flex items-center gap-2">
                Export Reports <ArrowUpRight size={16} />
             </button>
          </div>
        </header>

        {/* Dashboard Area */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8">
          <h1 className="text-2xl font-bold">Case Management</h1>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
             <StatCard 
                label="Total Active Cases" 
                value={cases.length.toString()} 
                trend="+12% from yesterday"
                icon={<Users className="text-blue-600"/>}
                bgColor="bg-blue-50"
             />
             <StatCard 
                label="Entitlement Value" 
                value={`₹${cases.reduce((acc, c) => acc + (c.total_entitlement || 0), 0).toLocaleString()}`} 
                trend="Locked for beneficiaries"
                icon={<FileCheck className="text-green-600"/>}
                bgColor="bg-green-50"
             />
             <StatCard 
                label="Avg Compliance" 
                value="84%" 
                trend="Based on 24 audits"
                icon={<AlertCircle className="text-amber-600"/>}
                bgColor="bg-amber-50"
             />
             <StatCard 
                label="Identity Confidence" 
                value="98.2%" 
                trend="ML Verification Active"
                icon={<ArrowUpRight className="text-purple-600"/>}
                bgColor="bg-purple-50"
             />
          </div>

          {/* Cases Table */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
             <div className="p-6 border-b border-zinc-100 flex items-center justify-between">
                <h2 className="font-bold text-lg">Active Applications</h2>
                <div className="flex gap-2">
                   <FilterBadge label="All Cases" active />
                   <FilterBadge label="Pending Audit" />
                   <FilterBadge label="High Priority" />
                </div>
             </div>
             <div className="overflow-x-auto">
                <table className="w-full text-left">
                   <thead className="bg-zinc-50 text-zinc-400 text-[10px] uppercase tracking-widest font-bold">
                      <tr>
                         <th className="px-6 py-4">Beneficiary</th>
                         <th className="px-6 py-4">State</th>
                         <th className="px-6 py-4">Compliance Audit</th>
                         <th className="px-6 py-4">Entitlement</th>
                         <th className="px-6 py-4">Status</th>
                         <th className="px-6 py-4 text-right">Action</th>
                      </tr>
                   </thead>
                   <tbody className="text-sm divide-y divide-zinc-100">
                      {loading ? (
                          <tr><td colSpan={6} className="px-6 py-12 text-center text-zinc-400 animate-pulse">Loading cases...</td></tr>
                      ) : cases.length === 0 ? (
                          <tr><td colSpan={6} className="px-6 py-12 text-center text-zinc-400 italic">No active cases found. Interaction will pop up here live.</td></tr>
                      ) : cases.map((c, idx) => (
                         <tr key={idx} className="hover:bg-zinc-50 transition-colors group">
                            <td className="px-6 py-4">
                               <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 bg-zinc-100 rounded-full flex items-center justify-center font-bold text-xs text-zinc-500">
                                     {c.name.charAt(0)}
                                  </div>
                                  <div>
                                     <p className="font-bold">{c.name}</p>
                                     <p className="text-xs text-zinc-400">{c.phone}</p>
                                  </div>
                               </div>
                            </td>
                            <td className="px-6 py-4 font-medium">{c.state}</td>
                            <td className="px-6 py-4">
                               <div className="flex flex-col gap-1">
                                  <div className="flex items-center justify-between text-[10px] font-bold">
                                     <span className={c.compliance_score === 'N/A' ? 'text-zinc-400' : 'text-blue-600'}>SCORE</span>
                                     <span>{c.compliance_score}%</span>
                                  </div>
                                  <div className="w-32 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                                     <div 
                                        className="h-full bg-blue-600 transition-all duration-1000" 
                                        style={{ width: `${c.compliance_score === 'N/A' ? 0 : c.compliance_score}%` }}
                                     ></div>
                                  </div>
                               </div>
                            </td>
                            <td className="px-6 py-4 font-bold">₹{(c.total_entitlement || 0).toLocaleString()}</td>
                            <td className="px-6 py-4">
                               <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-tight ${
                                  c.status === "Claim Filed" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"
                               }`}>
                                  {c.status}
                               </span>
                            </td>
                            <td className="px-6 py-4 text-right">
                               <button className="p-2 hover:bg-blue-50 text-zinc-400 hover:text-blue-600 transition-all rounded-lg">
                                  <ChevronRight size={18} />
                               </button>
                            </td>
                         </tr>
                      ))}
                   </tbody>
                </table>
             </div>
          </div>

          {/* Visual Escalation Ladder - Demo Style */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <h3 className="font-bold mb-4 flex items-center gap-2">
                   <AlertCircle size={18} className="text-red-500"/> System Health
                </h3>
                <div className="space-y-4">
                   <HealthBar label="Sarvam STT/TTS (Voice Native)" level={98} />
                   <HealthBar label="Gemini 1.5 Flash (Agent Logic)" level={100} />
                   <HealthBar label="Identity Reconciliation ML" level={94} />
                </div>
             </div>
             <div className="bg-gradient-to-br from-zinc-800 to-black p-6 rounded-xl text-white shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-20">
                   <LayoutDashboard size={120} />
                </div>
                <h3 className="font-bold mb-2 relative z-10">Live Audit Flow</h3>
                <p className="text-zinc-400 text-xs mb-6 relative z-10">Real-time processing of claim disputes.</p>
                <div className="space-y-4 relative z-10">
                   <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span className="text-sm font-medium">Auto-Quality Gate Active</span>
                   </div>
                   <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-75"></div>
                      <span className="text-sm font-medium">Reconciliation Engine Polling</span>
                   </div>
                   <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse delay-150"></div>
                      <span className="text-sm font-medium">Dispute Agent drafting legal objection</span>
                   </div>
                </div>
             </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function SidebarLink({ icon, label, active = false }: { icon: any, label: string, active?: boolean }) {
  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
      active ? 'bg-blue-50 text-blue-700 font-bold shadow-sm' : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
    }`}>
      {icon}
      <span className="text-sm">{label}</span>
    </div>
  )
}

function StatCard({ label, value, trend, icon, bgColor }: any) {
  return (
    <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm hover:shadow-md transition-all">
       <div className={`${bgColor} w-10 h-10 rounded-lg flex items-center justify-center mb-4`}>
          {icon}
       </div>
       <p className="text-xs font-bold text-zinc-400 uppercase tracking-widest">{label}</p>
       <h3 className="text-2xl font-bold mt-1">{value}</h3>
       <p className="text-[10px] font-medium text-zinc-400 mt-1">{trend}</p>
    </div>
  )
}

function FilterBadge({ label, active = false }: any) {
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold cursor-pointer transition-all ${
      active ? 'bg-zinc-900 text-white shadow-sm' : 'bg-zinc-100 text-zinc-500 hover:bg-zinc-200'
    }`}>
      {label}
    </span>
  )
}

function HealthBar({ label, level }: any) {
  return (
    <div className="space-y-1.5">
       <div className="flex justify-between text-xs font-bold">
          <span className="text-zinc-500">{label}</span>
          <span>{level}%</span>
       </div>
       <div className="w-full h-1.5 bg-zinc-100 rounded-full overflow-hidden">
          <div className="h-full bg-green-500" style={{ width: `${level}%` }}></div>
       </div>
    </div>
  )
}
