"use client";

import { useState } from "react";
import { Heart, Share2, Play, Clock, TrendingUp, MessageSquare } from "lucide-react";

interface ClipData {
  id: string;
  title: string;
  thumbnail?: string;
  duration: number;
  views: number;
  likes: number;
  createdAt: string;
  streamer: {
    name: string;
    avatar?: string;
  };
  tags: string[];
  heatScore: number;
}

interface ViewerDashboardModernProps {
  streamer: {
    id: string;
    name: string;
    avatar?: string;
    followers: number;
    isLive: boolean;
  };
  clips: ClipData[];
  isLoading?: boolean;
}

export function ClipCardModern({ clip }: { clip: ClipData }) {
  const [liked, setLiked] = useState(false);

  return (
    <div
      className="group rounded-2xl overflow-hidden bg-gradient-to-br from-slate-700
                 to-slate-800 border border-white/10 hover:border-purple-500/30
                 transition-all hover:shadow-xl hover:shadow-purple-600/20
                 transform hover:scale-105 duration-300 cursor-pointer"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-slate-900 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent z-10" />
        {clip.thumbnail ? (
          <img
            src={clip.thumbnail}
            alt={clip.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-slate-800">
            <Play className="w-12 h-12 text-gray-500 opacity-50" />
          </div>
        )}

        {/* Duration Badge */}
        <div className="absolute bottom-3 right-3 flex items-center gap-1 px-2 py-1
                       bg-black/80 rounded-md text-white text-xs font-bold z-20">
          <Clock className="w-3 h-3" />
          {clip.duration}s
        </div>

        {/* Heat Score Badge */}
        {clip.heatScore > 70 && (
          <div className="absolute top-3 right-3 flex items-center gap-1 px-2.5 py-1.5
                        bg-gradient-to-r from-amber-500 to-orange-500 rounded-full
                        text-white text-xs font-bold z-20">
            <TrendingUp className="w-3 h-3" />
            Trending
          </div>
        )}

        {/* Play Button Overlay */}
        <div
          className="absolute inset-0 flex items-center justify-center z-15
                   opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <div
            className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm
                      flex items-center justify-center hover:bg-white/30"
          >
            <Play className="w-6 h-6 text-white fill-white ml-0.5" />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Streamer Info */}
        <div className="flex items-center gap-2 mb-3">
          {clip.streamer.avatar ? (
            <img
              src={clip.streamer.avatar}
              alt={clip.streamer.name}
              className="w-6 h-6 rounded-full"
            />
          ) : (
            <div className="w-6 h-6 rounded-full bg-purple-600" />
          )}
          <span className="text-xs font-semibold text-gray-300">
            {clip.streamer.name}
          </span>
        </div>

        {/* Title */}
        <h3 className="font-bold text-sm mb-2 line-clamp-2 text-white
                      group-hover:text-purple-300 transition-colors">
          {clip.title}
        </h3>

        {/* Metadata */}
        <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3" />
            {(clip.views / 1000).toFixed(1)}k
          </span>
          <span className="flex items-center gap-1">
            <Heart className="w-3 h-3" />
            {(clip.likes / 1000).toFixed(1)}k
          </span>
        </div>

        {/* Tags */}
        <div className="flex gap-2 mb-3 flex-wrap">
          {clip.tags.slice(0, 2).map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 rounded-full bg-purple-600/30 text-purple-300
                       text-xs font-medium border border-purple-500/30"
            >
              #{tag}
            </span>
          ))}
        </div>

        {/* Action Buttons */}
        <div
          className="flex gap-2 opacity-0 group-hover:opacity-100
                   transition-opacity pt-2 border-t border-white/10"
        >
          <button
            onClick={(e) => {
              e.preventDefault();
              setLiked(!liked);
            }}
            className={`flex-1 flex items-center justify-center gap-1 py-2 rounded-lg
                     text-xs font-semibold transition-all ${
                       liked
                         ? "bg-red-600 text-white"
                         : "bg-white/10 text-gray-300 hover:bg-white/20"
                     }`}
          >
            <Heart className={`w-3 h-3 ${liked ? "fill-current" : ""}`} />
            Like
          </button>
          <button
            className="flex-1 flex items-center justify-center gap-1 py-2 rounded-lg
                     bg-white/10 text-gray-300 hover:bg-white/20 text-xs font-semibold
                     transition-all"
          >
            <Share2 className="w-3 h-3" />
            Share
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ViewerDashboardModern({
  streamer,
  clips,
  isLoading = false,
}: ViewerDashboardModernProps) {
  const [sortBy, setSortBy] = useState<"trending" | "newest" | "most-liked">(
    "trending"
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Streamer Header */}
      <div
        className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900
                  border-b border-white/10 p-6 md:p-8"
      >
        <div className="flex items-start gap-6 mb-6">
          {streamer.avatar ? (
            <img
              src={streamer.avatar}
              alt={streamer.name}
              className="w-20 h-20 rounded-2xl"
            />
          ) : (
            <div className="w-20 h-20 rounded-2xl bg-purple-600" />
          )}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-black text-white">{streamer.name}</h1>
              {streamer.isLive && (
                <span
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-full
                           bg-red-600 text-white text-xs font-bold"
                >
                  <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  LIVE
                </span>
              )}
            </div>
            <p className="text-gray-400">
              {streamer.followers.toLocaleString()} followers
            </p>
          </div>
        </div>

        {/* Sort Options */}
        <div className="flex gap-2">
          {(["trending", "newest", "most-liked"] as const).map((option) => (
            <button
              key={option}
              onClick={() => setSortBy(option)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                sortBy === option
                  ? "bg-purple-600 text-white"
                  : "bg-white/10 text-gray-300 hover:bg-white/20"
              }`}
            >
              {option === "trending"
                ? "🔥 Trending"
                : option === "newest"
                  ? "✨ Newest"
                  : "❤️ Most Liked"}
            </button>
          ))}
        </div>
      </div>

      {/* Clips Grid */}
      <div className="p-6 md:p-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-purple-600/20 border-t-purple-600
                          rounded-full animate-spin" />
          </div>
        ) : clips.length === 0 ? (
          <div className="text-center py-20">
            <MessageSquare className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-400 mb-2">
              No clips yet
            </h3>
            <p className="text-gray-500">
              Check back soon or ask the streamer to create some clips!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {clips.map((clip) => (
              <ClipCardModern key={clip.id} clip={clip} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
