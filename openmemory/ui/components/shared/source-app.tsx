import React from "react";
import { BiEdit } from "react-icons/bi";
import Image from "next/image";

export const Icon = ({ source }: { source: string }) => {
  return (
    <div className="w-4 h-4 rounded-full bg-zinc-700 flex items-center justify-center overflow-hidden -mr-1">
      <Image src={source} alt={source} width={40} height={40} />
    </div>
  );
};

export const constants = {
  claude: {
    name: "Claude Web",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "claude-desktop": {
    name: "Claude Desktop",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "claude-code": {
    name: "Claude Code",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude Claude Desktop (SSE)": {
    name: "Claude Desktop (SSE)",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude Code": {
    name: "Claude Code (VS Code)",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude VS Code": {
    name: "Claude VS Code",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp", 
  },
  "Claude VS Code Extension": {
    name: "Claude for VS Code",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude Web (Chrome)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Claude Web (Firefox)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Claude Web (Safari)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Claude Web (Edge)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Claude Mobile": {
    name: "Claude Mobile",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude Web": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  // New Untagged patterns
  "Untagged (Chrome)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Untagged (Firefox)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Untagged (Safari)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Untagged (Edge)": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "Untagged": {
    name: "Untagged",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  openmemory: {
    name: "OpenMemory",
    icon: <Icon source="/images/open-memory.svg" />,
    iconImage: "/images/open-memory.svg",
  },
  cursor: {
    name: "Cursor",
    icon: <Icon source="/images/cursor.png" />,
    iconImage: "/images/cursor.png",
  },
  cline: {
    name: "Cline",
    icon: <Icon source="/images/cline.png" />,
    iconImage: "/images/cline.png",
  },
  roocline: {
    name: "Roo Cline",
    icon: <Icon source="/images/roocline.png" />,
    iconImage: "/images/roocline.png",
  },
  windsurf: {
    name: "Windsurf",
    icon: <Icon source="/images/windsurf.png" />,
    iconImage: "/images/windsurf.png",
  },
  witsy: {
    name: "Witsy",
    icon: <Icon source="/images/witsy.png" />,
    iconImage: "/images/witsy.png",
  },
  enconvo: {
    name: "Enconvo",
    icon: <Icon source="/images/enconvo.png" />,
    iconImage: "/images/enconvo.png",
  },
  augment: {
    name: "Augment",
    icon: <Icon source="/images/augment.png" />,
    iconImage: "/images/augment.png",
  },
  "Claude Claude Desktop (SSE)": {
    name: "Claude Desktop",
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "Claude Desktop": {
    name: "Claude Desktop", 
    icon: <Icon source="/images/claude.webp" />,
    iconImage: "/images/claude.webp",
  },
  "local-user": {
    name: "Local User",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "mcp-client": {
    name: "MCP Client",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  "test-client": {
    name: "Test Client", 
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
  // Ollama Models
  "ollama-llama3.1:8b": {
    name: "Llama 3.1 8B",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">🦙</div>,
    iconImage: null,
  },
  "ollama-deepseek-r1:latest": {
    name: "DeepSeek R1",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xs font-bold">🧠</div>,
    iconImage: null,
  },
  "ollama-mistral:7b": {
    name: "Mistral 7B",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xs font-bold">M</div>,
    iconImage: null,
  },
  "ollama-codellama:13b": {
    name: "Code Llama 13B",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xs font-bold">💻</div>,
    iconImage: null,
  },
  "ollama-qwen2:7b": {
    name: "Qwen2 7B",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-yellow-500 to-red-600 flex items-center justify-center text-white text-xs font-bold">Q</div>,
    iconImage: null,
  },
  "ollama-phi4:latest": {
    name: "Phi-4",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white text-xs font-bold">Φ</div>,
    iconImage: null,
  },
  "ollama-gemma3:latest": {
    name: "Gemma 3",
    icon: <div className="w-4 h-4 rounded-full bg-gradient-to-br from-pink-500 to-red-600 flex items-center justify-center text-white text-xs font-bold">💎</div>,
    iconImage: null,
  },
  default: {
    name: "Default",
    icon: <BiEdit size={18} className="ml-1" />,
    iconImage: "/images/default.png",
  },
};

const SourceApp = ({ source }: { source: string }) => {
  const appConfig = constants[source as keyof typeof constants];
  
  if (!appConfig) {
    // If no matching config found, use the actual source name instead of "Default"
    return (
      <div className="flex items-center gap-2">
        <BiEdit size={18} className="ml-1" />
        <span className="text-sm font-semibold">{source}</span>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-2">
      {appConfig.icon}
      <span className="text-sm font-semibold">
        {appConfig.name}
      </span>
    </div>
  );
};

export default SourceApp;
