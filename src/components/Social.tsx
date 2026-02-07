import { useState } from 'react';
import { PhoneFrame } from './PhoneFrame';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from './ThemeContext';
import { Heart, MessageCircle, Share2, MapPin, TrendingUp, Radio, Search, UserPlus, Send, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Post {
  id: number;
  user: string;
  avatar: string;
  time: string;
  content: string;
  location: string;
  likes: number;
  comments: number;
  type: 'alert' | 'update';
  liked?: boolean;
}

export function Social() {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState<'feed' | 'friends'>('feed');
  const [searchQuery, setSearchQuery] = useState('');
  const [commentPostId, setCommentPostId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');

  const [posts, setPosts] = useState<Post[]>([
    {
      id: 1,
      user: 'Alex Rodriguez',
      avatar: '👨‍🎨',
      time: '8m',
      content: theme === 'stranger'
        ? 'LOT B IS PACKED. Circled 3x. AVOID!!! 😤'
        : 'Lot B is packed right now 😤 Had to circle 3 times. Avoid if possible!',
      location: theme === 'stranger' ? 'LOT B / BUSCH' : 'Lot B • Busch',
      likes: 24,
      comments: 7,
      type: 'alert',
      liked: false,
    },
    {
      id: 2,
      user: 'Jessica Park',
      avatar: '👩‍🚀',
      time: '15m',
      content: theme === 'stranger'
        ? 'Found spot in LOT C ROW 4! Plenty near SEC building ✨'
        : 'Just found a spot in Lot C Row 4! Plenty of spaces available near SEC building ✨',
      location: theme === 'stranger' ? 'LOT C / BUSCH' : 'Lot C • Busch',
      likes: 42,
      comments: 12,
      type: 'update',
      liked: false,
    },
    {
      id: 3,
      user: 'David Kim',
      avatar: '👨‍🔧',
      time: '32m',
      content: theme === 'stranger'
        ? 'CONSTRUCTION on Yellow entrance. Use REAR entrance! 🚧'
        : 'PSA: Construction on Yellow lot entrance. Use the rear entrance instead 🚧',
      location: theme === 'stranger' ? 'YELLOW LOT / C.AVE' : 'Yellow Lot • College Ave',
      likes: 67,
      comments: 15,
      type: 'alert',
      liked: false,
    },
    {
      id: 4,
      user: 'Rachel Green',
      avatar: '👩‍🎤',
      time: '1h',
      content: theme === 'stranger'
        ? 'Early bird gets the spot 🎯 Front row victory!'
        : 'Early morning parking is a blessing ✨ Got a front row spot for once!',
      location: theme === 'stranger' ? 'LOT A / LIVINGSTON' : 'Lot A • Livingston',
      likes: 18,
      comments: 5,
      type: 'update',
      liked: false,
    },
  ]);

  const [friends, setFriends] = useState([
    { id: 1, name: 'Sarah Chen', status: 'PARKED @ LOT C', time: '5m', avatar: '👩‍💻', active: true, following: true },
    { id: 2, name: 'Mike Johnson', status: 'SEARCHING...', time: '12m', avatar: '👨‍🎓', active: true, following: true },
    { id: 3, name: 'Emma Wilson', status: 'EN ROUTE', time: '23m', avatar: '👩‍🔬', active: false, following: true },
    { id: 4, name: 'James Lee', status: 'PARKED @ LOT A', time: '1h', avatar: '👨‍💼', active: false, following: true },
  ]);

  const [searchResults, setSearchResults] = useState([
    { id: 5, name: 'Tom Anderson', avatar: '👨‍🏫', mutualFriends: 3, following: false },
    { id: 6, name: 'Lisa Wang', avatar: '👩‍⚕️', mutualFriends: 7, following: false },
    { id: 7, name: 'Chris Martinez', avatar: '👨‍🚒', mutualFriends: 2, following: false },
  ]);

  const trendingTopics = theme === 'stranger'
    ? [
      { tag: '#LOTBFULL', count: 234 },
      { tag: '#EARLYBIRD', count: 189 },
      { tag: '#PARKINGTIPS', count: 156 },
    ]
    : [
      { tag: '#LotBFull', count: 234 },
      { tag: '#EarlyBirdWins', count: 189 },
      { tag: '#ParkingTips', count: 156 },
    ];

  const handleLike = (postId: number) => {
    setPosts(posts.map(post =>
      post.id === postId
        ? { ...post, liked: !post.liked, likes: post.liked ? post.likes - 1 : post.likes + 1 }
        : post
    ));
  };

  const handleComment = (postId: number) => {
    if (commentText.trim()) {
      setPosts(posts.map(post =>
        post.id === postId
          ? { ...post, comments: post.comments + 1 }
          : post
      ));
      setCommentText('');
      setCommentPostId(null);
    }
  };

  const handleFollowToggle = (userId: number) => {
    setSearchResults(searchResults.map(user =>
      user.id === userId
        ? { ...user, following: !user.following }
        : user
    ));
  };

  const filteredSearchResults = searchResults.filter(user =>
    user.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <PhoneFrame>
      <div className={`min-h-full ${theme === 'stranger' ? 'scanlines' : ''}`}>
        {/* Header */}
        <div className={`px-6 pt-3 pb-3 ${theme === 'stranger' ? 'border-b-2 border-red-600/30' : 'border-b border-gray-700'
          }`}>
          <div className="flex items-center justify-between mb-3">
            <h1 className={`text-3xl tracking-wider ${theme === 'stranger'
              ? "font-['Bebas_Neue'] text-red-600 glow-text"
              : 'font-bold text-red-500'
              }`}>
              {theme === 'stranger' ? 'SOCIAL' : 'Social'}
            </h1>
            <ThemeToggle />
          </div>
        </div>

        {/* Tab Switcher - Integrated Design */}
        <div className={`px-6 pt-3 pb-3 ${theme === 'stranger' ? 'border-b border-red-600/30' : 'border-b border-gray-700'
          }`}>
          <div className={`relative flex p-1 rounded-xl ${theme === 'stranger'
              ? 'bg-red-950/20 border border-red-900/40'
              : 'bg-gray-800/50 border border-white/5'
            }`}>
            <button
              onClick={() => setActiveTab('feed')}
              className={`relative flex-1 py-2 text-center text-sm font-bold tracking-wider transition-colors z-10 outline-none ${activeTab === 'feed'
                  ? 'text-white'
                  : theme === 'stranger' ? 'text-red-600/60 hover:text-red-500' : 'text-gray-500 hover:text-gray-300'
                } ${theme === 'stranger' ? "font-['Bebas_Neue'] text-base" : ''}`}
            >
              {activeTab === 'feed' && (
                <motion.div
                  layoutId="activeTab"
                  className={`absolute inset-0 rounded-lg ${theme === 'stranger'
                      ? 'bg-red-600 shadow-[0_0_15px_rgba(220,38,38,0.5)]'
                      : 'bg-gray-700 shadow-sm'
                    }`}
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}
              <span className="relative z-10">FEED</span>
            </button>
            <button
              onClick={() => setActiveTab('friends')}
              className={`relative flex-1 py-2 text-center text-sm font-bold tracking-wider transition-colors z-10 outline-none ${activeTab === 'friends'
                  ? 'text-white'
                  : theme === 'stranger' ? 'text-red-600/60 hover:text-red-500' : 'text-gray-500 hover:text-gray-300'
                } ${theme === 'stranger' ? "font-['Bebas_Neue'] text-base" : ''}`}
            >
              {activeTab === 'friends' && (
                <motion.div
                  layoutId="activeTab"
                  className={`absolute inset-0 rounded-lg ${theme === 'stranger'
                      ? 'bg-red-600 shadow-[0_0_15px_rgba(220,38,38,0.5)]'
                      : 'bg-gray-700 shadow-sm'
                    }`}
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}
              <span className="relative z-10">FRIENDS</span>
            </button>
          </div>
        </div>

        {activeTab === 'friends' ? (
          <div className="px-6 py-4 space-y-3">
            {/* Search Bar */}
            <div className={`relative ${theme === 'stranger' ? 'border border-red-600/40' : 'border border-gray-700 rounded-lg'
              }`}>
              <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${theme === 'stranger' ? 'text-red-600' : 'text-gray-500'
                }`} />
              <input
                type="text"
                placeholder={theme === 'stranger' ? 'SEARCH USERS...' : 'Search users...'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`w-full py-2.5 pl-10 pr-3 bg-transparent font-mono text-sm text-white placeholder-gray-500 focus:outline-none ${theme === 'stranger' ? '' : 'rounded-lg'
                  }`}
              />
            </div>

            {/* Search Results */}
            {searchQuery && filteredSearchResults.length > 0 && (
              <div className="space-y-2 mb-4">
                <h3 className={`text-xs ${theme === 'stranger' ? "text-red-600 font-['Bebas_Neue'] tracking-wider" : 'text-red-500 font-semibold'
                  }`}>
                  {theme === 'stranger' ? 'SEARCH RESULTS' : 'Search Results'}
                </h3>
                {filteredSearchResults.map((user) => (
                  <motion.div
                    key={user.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={theme === 'stranger'
                      ? 'bg-black border border-red-600/40 p-3'
                      : 'bg-gray-900 border border-gray-700 rounded-lg p-3'
                    }
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-2xl">{user.avatar}</div>
                      <div className="flex-1">
                        <h3 className={theme === 'stranger'
                          ? "text-white font-['Bebas_Neue'] tracking-wider"
                          : 'text-white font-semibold'
                        }>
                          {user.name}
                        </h3>
                        <div className="text-xs text-gray-400 font-mono">
                          {user.mutualFriends} mutual friends
                        </div>
                      </div>
                      <button
                        onClick={() => handleFollowToggle(user.id)}
                        className={`p-2 transition-colors ${user.following
                          ? theme === 'stranger'
                            ? 'text-red-600 bg-red-600/20'
                            : 'text-red-500 bg-red-500/20 rounded-lg'
                          : theme === 'stranger'
                            ? 'text-green-500 bg-green-500/20 hover:bg-green-500/30'
                            : 'text-green-400 bg-green-400/20 hover:bg-green-400/30 rounded-lg'
                          }`}
                      >
                        <UserPlus className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Friends List */}
            <h3 className={`text-xs mt-4 ${theme === 'stranger' ? "text-red-600 font-['Bebas_Neue'] tracking-wider" : 'text-red-500 font-semibold'
              }`}>
              {theme === 'stranger' ? 'YOUR FRIENDS' : 'Your Friends'}
            </h3>
            {friends.map((friend, index) => (
              <motion.div
                key={friend.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={theme === 'stranger'
                  ? 'bg-black border border-red-600/40 p-4 hover:border-red-600/80 transition-colors'
                  : 'bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-red-500 transition-colors'
                }
              >
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="text-3xl">{friend.avatar}</div>
                    {friend.active && (
                      <div className={`absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse ${theme === 'stranger' ? 'shadow-[0_0_8px_rgba(0,255,0,0.8)]' : ''
                        }`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className={theme === 'stranger'
                      ? "text-white font-['Bebas_Neue'] tracking-wider"
                      : 'text-white font-semibold'
                    }>
                      {friend.name}
                    </h3>
                    <div className="text-xs text-gray-400 font-mono">{friend.status}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500 font-mono">{friend.time}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-4 space-y-3">
            {/* Community Stats */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={theme === 'stranger'
                ? 'bg-black border-2 border-red-600 p-4 relative mb-4'
                : 'bg-gray-900 border border-red-500 rounded-lg p-4 mb-4'
              }
            >
              {theme === 'stranger' && (
                <>
                  <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-600" />
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-600" />
                </>
              )}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Radio className={`w-5 h-5 ${theme === 'stranger' ? 'text-red-600 animate-pulse' : 'text-red-500'
                    }`} />
                  <div>
                    <div className="text-xs text-gray-400">
                      {theme === 'stranger' ? 'ACTIVE NOW' : 'Active Now'}
                    </div>
                    <div className={`text-2xl font-bold font-mono ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                      }`}>1,247</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-400">
                    {theme === 'stranger' ? 'POSTS TODAY' : 'Posts Today'}
                  </div>
                  <div className={`text-2xl font-bold font-mono ${theme === 'stranger' ? 'text-green-500' : 'text-green-400'
                    }`}>456</div>
                </div>
              </div>
            </motion.div>

            {/* Trending Topics */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className={theme === 'stranger'
                ? 'bg-black border border-red-600/40 p-3 mb-4'
                : 'bg-gray-900 border border-gray-700 rounded-lg p-3 mb-4'
              }
            >
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className={`w-4 h-4 ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'}`} />
                <h3 className={`text-xs ${theme === 'stranger'
                  ? "font-['Bebas_Neue'] tracking-wider text-red-600"
                  : 'font-semibold text-red-500'
                  }`}>
                  {theme === 'stranger' ? 'TRENDING TOPICS' : 'Trending Topics'}
                </h3>
              </div>
              <div className="flex gap-2 flex-wrap">
                {trendingTopics.map((topic, index) => (
                  <button
                    key={index}
                    className={`px-2 py-1 text-xs font-mono transition-colors ${theme === 'stranger'
                      ? 'bg-red-600/20 border border-red-600/40 text-red-600 hover:bg-red-600/30'
                      : 'bg-red-500/20 border border-red-500/40 text-red-500 hover:bg-red-500/30 rounded'
                      }`}
                  >
                    {topic.tag} <span className="text-gray-500">({topic.count})</span>
                  </button>
                ))}
              </div>
            </motion.div>

            {/* Posts Feed */}
            {posts.map((post, index) => (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={theme === 'stranger'
                  ? 'bg-black border border-red-600/40 hover:border-red-600/80 transition-colors'
                  : 'bg-gray-900 border border-gray-700 hover:border-red-500 rounded-lg transition-colors'
                }
              >
                <div className="p-4">
                  {/* User Header */}
                  <div className="flex items-start gap-3 mb-3">
                    <div className="text-2xl">{post.avatar}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className={theme === 'stranger'
                          ? "text-white font-['Bebas_Neue'] tracking-wider"
                          : 'text-white font-semibold'
                        }>
                          {post.user}
                        </h4>
                        {post.type === 'alert' && (
                          <span className={`text-xs text-white px-2 py-0.5 font-mono ${theme === 'stranger' ? 'bg-red-600' : 'bg-red-500 rounded'
                            }`}>
                            ALERT
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-gray-500 font-mono">{post.time}</span>
                        <span className="text-gray-600">|</span>
                        <MapPin className="w-3 h-3 text-gray-500" />
                        <span className="text-gray-500 font-mono">{post.location}</span>
                      </div>
                    </div>
                  </div>

                  {/* Content */}
                  <p className="text-white mb-3 font-mono text-sm leading-relaxed">
                    {post.content}
                  </p>

                  {/* Actions */}
                  <div className={`flex items-center gap-6 pt-3 ${theme === 'stranger' ? 'border-t border-red-600/30' : 'border-t border-gray-700'
                    }`}>
                    <button
                      onClick={() => handleLike(post.id)}
                      className={`flex items-center gap-2 transition-colors ${post.liked
                        ? theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                        : 'text-gray-400'
                        } ${theme === 'stranger' ? 'hover:text-red-600' : 'hover:text-red-500'
                        }`}
                    >
                      <Heart className={`w-4 h-4 ${post.liked ? 'fill-current' : ''}`} />
                      <span className="text-sm font-mono">{post.likes}</span>
                    </button>
                    <button
                      onClick={() => setCommentPostId(post.id === commentPostId ? null : post.id)}
                      className={`flex items-center gap-2 text-gray-400 transition-colors ${theme === 'stranger' ? 'hover:text-red-600' : 'hover:text-red-500'
                        }`}
                    >
                      <MessageCircle className="w-4 h-4" />
                      <span className="text-sm font-mono">{post.comments}</span>
                    </button>
                    <button className={`flex items-center gap-2 text-gray-400 transition-colors ml-auto ${theme === 'stranger' ? 'hover:text-red-600' : 'hover:text-red-500'
                      }`}>
                      <Share2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Comment Input */}
                  <AnimatePresence>
                    {commentPostId === post.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className={`mt-3 pt-3 ${theme === 'stranger' ? 'border-t border-red-600/30' : 'border-t border-gray-700'
                          }`}
                      >
                        <div className={`flex gap-2 ${theme === 'stranger' ? 'border border-red-600/40' : 'border border-gray-700 rounded-lg'
                          }`}>
                          <input
                            type="text"
                            placeholder={theme === 'stranger' ? 'ADD COMMENT...' : 'Add a comment...'}
                            value={commentText}
                            onChange={(e) => setCommentText(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleComment(post.id)}
                            className={`flex-1 py-2 px-3 bg-transparent font-mono text-sm text-white placeholder-gray-500 focus:outline-none ${theme === 'stranger' ? '' : 'rounded-lg'
                              }`}
                          />
                          <button
                            onClick={() => handleComment(post.id)}
                            disabled={!commentText.trim()}
                            className={`p-2 transition-colors ${commentText.trim()
                              ? theme === 'stranger'
                                ? 'text-red-600 hover:bg-red-600/20'
                                : 'text-red-500 hover:bg-red-500/20 rounded-lg'
                              : 'text-gray-600 cursor-not-allowed'
                              }`}
                          >
                            <Send className="w-4 h-4" />
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            ))}

            {/* Load More */}
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className={`w-full py-3 text-gray-400 hover:text-white transition-colors ${theme === 'stranger'
                ? "bg-black border border-red-600/40 hover:border-red-600 font-['Bebas_Neue'] tracking-wider"
                : 'bg-gray-900 border border-gray-700 hover:border-red-500 rounded-lg font-semibold'
                }`}
            >
              {theme === 'stranger' ? 'LOAD MORE' : 'Load More Posts'}
            </motion.button>
          </div>
        )}
      </div>
    </PhoneFrame>
  );
}