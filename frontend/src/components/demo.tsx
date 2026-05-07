"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { AIChatInput } from "@/components/ui/ai-chat-input"
import { 
  Home, 
  Compass, 
  Library, 
  Plus, 
  MessageSquare, 
  ChevronRight,
  Share,
  MoreHorizontal
} from "lucide-react"

const API_BASE = "http://localhost:8000"

interface Message {
  direction: "in" | "out"
  text?: string
  audio?: string
  image?: string
}

const Demo = () => {
  const [phone, setPhone] = useState("917702919936")
  const [messages, setMessages] = useState<Message[]>([])
  const chatContainerRef = React.useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const fetchMessages = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/messages/${phone}`)
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch (err) {
      console.error("Polling error:", err)
    }
  }

  useEffect(() => {
    fetchMessages()
    const interval = setInterval(fetchMessages, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleSend = async (text: string) => {
    try {
      await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, text }),
      })
      fetchMessages()
    } catch (err) {
      console.error("Send error:", err)
    }
  }

  const handleImageUpload = async (image_data: string) => {
    try {
      await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, image_data }),
      })
      fetchMessages()
    } catch (err) {
      console.error("Image upload error:", err)
    }
  }

  const handleVoiceUpload = async (audio_data: string) => {
    try {
      await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, audio_data }),
      })
      fetchMessages()
    } catch (err) {
      console.error("Voice upload error:", err)
    }
  }

  return (
    <div className="flex h-screen w-screen bg-white text-zinc-900 font-sans selection:bg-blue-100">
      {/* Sidebar - Perplexity Style */}
      <aside className="w-64 border-r border-zinc-100 flex flex-col bg-zinc-50/50 hidden md:flex">
        <div className="p-6 flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center text-white font-bold">H</div>
          <span className="font-bold text-xl tracking-tight">Haqdaar</span>
        </div>

        <button className="mx-4 mb-6 flex items-center justify-between px-4 py-2 bg-white border border-zinc-200 rounded-full text-sm font-medium hover:shadow-sm transition-all group">
          <span>New Thread</span>
          <div className="flex items-center gap-1 opacity-50 group-hover:opacity-100 transition-opacity">
            <span className="text-xs">Ctrl I</span>
          </div>
        </button>

        <nav className="flex-1 px-4 space-y-1">
          <SidebarItem icon={<Home size={18}/>} label="Home" active />
          <SidebarItem icon={<Compass size={18}/>} label="Discover" />
          <SidebarItem icon={<Library size={18}/>} label="Library" />
        </nav>

        <div className="p-4 border-t border-zinc-100">
          <div className="mb-4">
            <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1 block">Test Phone Number</label>
            <input 
                type="text" 
                value={phone} 
                onChange={(e) => setPhone(e.target.value)}
                className="w-full bg-zinc-100 border-none rounded-md px-3 py-1.5 text-xs focus:ring-1 focus:ring-blue-500 outline-none font-mono"
            />
          </div>
          <div className="flex items-center gap-3 p-2 hover:bg-zinc-100 rounded-lg cursor-pointer transition-colors">
            <div className="w-8 h-8 bg-zinc-200 rounded-full flex items-center justify-center">VN</div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">Vaibhav Nagdeo</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-white relative">
        {/* Top Header */}
        <header className="h-14 border-b border-zinc-50 flex items-center justify-between px-6 sticky top-0 bg-white/80 backdrop-blur-md z-20">
          <div className="flex items-center gap-4 text-sm font-medium text-zinc-500">
             <MessageSquare size={16} />
             <span>Current Thread</span>
          </div>
          <div className="flex items-center gap-3">
             <button className="p-2 hover:bg-zinc-100 rounded-full transition-colors"><Share size={18} className="text-zinc-500"/></button>
             <button className="p-2 hover:bg-zinc-100 rounded-full transition-colors"><MoreHorizontal size={18} className="text-zinc-500"/></button>
          </div>
        </header>

        {/* Scrollable Chat Area */}
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-4 py-8 md:px-0"
        >
          <div className="max-w-3xl mx-auto space-y-12 pb-32">
            {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-64 text-zinc-400">
                    <p className="text-2xl font-semibold text-zinc-300">How can I help you today?</p>
                </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className="group animate-in fade-in slide-in-from-bottom-4 duration-500">
                {msg.direction === "out" ? (
                  /* User Question */
                  <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-medium tracking-tight text-zinc-900 leading-tight">
                        {msg.text || (msg.image ? "Uploaded a document" : "Sent a voice message")}
                    </h1>
                  </div>
                ) : (
                  /* AI Response */
                  <div className="space-y-4 pt-2 border-t border-zinc-50 mt-8">
                    <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 bg-black rounded flex items-center justify-center text-white text-[10px] font-bold">H</div>
                        <span className="text-xs font-bold tracking-widest uppercase text-zinc-400">Haqdaar AI</span>
                    </div>
                    
                    <div className="prose prose-zinc max-w-none text-zinc-800 text-[16px] leading-[1.6]">
                       {msg.text && <div className="whitespace-pre-wrap">{msg.text}</div>}
                       
                       {msg.image && (
                         <div className="mt-4 rounded-xl overflow-hidden border border-zinc-200 shadow-sm">
                            <img src={msg.image} alt="Upload" className="w-full h-auto" />
                         </div>
                       )}

                       {msg.audio && (
                         <div className="mt-4 p-4 bg-zinc-50 rounded-xl border border-zinc-100 flex items-center gap-3">
                            <audio controls className="h-10 flex-1">
                                <source src={msg.audio.startsWith('data:') ? msg.audio : `data:audio/wav;base64,${msg.audio}`} />
                            </audio>
                         </div>
                       )}

                       {msg.file && (
                         <div className="mt-4 p-3 bg-blue-50 rounded-xl border border-blue-100 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white">
                                    <FileText size={16} />
                                </div>
                                <span className="text-xs font-medium text-blue-900">Claim_Letter.pdf</span>
                            </div>
                            <button 
                                onClick={() => {
                                    const link = document.createElement('a');
                                    link.href = `data:application/pdf;base64,${msg.file}`;
                                    link.download = "Claim_Letter.pdf";
                                    link.click();
                                }}
                                className="text-[10px] bg-white border border-blue-200 text-blue-600 px-3 py-1 rounded-md hover:bg-blue-50 transition-colors font-bold uppercase tracking-wider"
                            >
                                Download
                            </button>
                         </div>
                       )}
                    </div>

                    <div className="flex items-center gap-4 pt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="text-xs font-medium text-zinc-400 hover:text-zinc-600 transition-colors uppercase tracking-wider">Copy</button>
                        <button className="text-xs font-medium text-zinc-400 hover:text-zinc-600 transition-colors uppercase tracking-wider">Rewrite</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Floating Input Area - Centered at Bottom */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-white via-white to-transparent pointer-events-none">
          <div className="max-w-3xl mx-auto pointer-events-auto">
            <AIChatInput 
                onSend={handleSend} 
                onImageUpload={handleImageUpload}
                onVoiceUpload={handleVoiceUpload}
            />
            <p className="text-center text-[11px] text-zinc-400 mt-3 font-medium">
                Haqdaar AI can make mistakes. Check important legal info.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

const SidebarItem = ({ icon, label, active = false }: { icon: React.ReactNode, label: string, active?: boolean }) => (
  <div className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all ${active ? 'bg-zinc-200/50 text-black font-semibold' : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'}`}>
    {icon}
    <span className="text-sm">{label}</span>
  </div>
)

export { Demo }
