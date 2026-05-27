import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { motion } from 'framer-motion';

export default function OnboardingPage({ onComplete }) {
  const { createUser, generatePairCode, joinCouple } = useAuth();
  const [step, setStep] = useState('name');
  const [name, setName] = useState('');
  const [pairCode, setPairCode] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [mode, setMode] = useState(null);

  const handleCreateUser = async () => {
    if (!name.trim()) return;
    await createUser(name);
    setStep('mode');
  };

  const handleGenerateCode = async () => {
    const code = await generatePairCode();
    setGeneratedCode(code);
    setStep('waiting');
  };

  const handleJoinCode = async () => {
    if (!pairCode.trim() || pairCode.length !== 6) return;
    try {
      await joinCouple(pairCode);
      onComplete();
    } catch (error) {
      alert('Invalid pairing code or code already used');
    }
  };

  return (
    <div className="min-h-screen bg-[#FFF9F0] flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img
            src="https://static.prod-images.emergentagent.com/jobs/8b85d457-dc7c-433b-90f1-7f21f596c0e8/images/31fde269e39fc2ca86dac4b7dbaf37cd6dd0c99a2897a3acd6daa943002b4ad5.png"
            alt="Memory Link"
            className="w-24 h-24"
          />
        </div>

        <div className="bg-white border-2 border-[#121212] rounded-3xl p-8 neo-brutal-shadow-lg">
          {step === 'name' && (
            <>
              <h1 className="text-3xl font-bold mb-2 text-center" data-testid="onboarding-title">Welcome to Memory Link</h1>
              <p className="text-[#52525B] text-center mb-6">Share your moments together</p>

              <div className="space-y-4">
                <Input
                  data-testid="name-input"
                  placeholder="What's your name?"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleCreateUser()}
                  className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 focus-visible:bg-[#FFF9F0] neo-brutal-shadow text-lg p-6"
                />

                <Button
                  data-testid="continue-button"
                  onClick={handleCreateUser}
                  disabled={!name.trim()}
                  className="w-full bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
                >
                  Continue
                </Button>
              </div>
            </>
          )}

          {step === 'mode' && (
            <>
              <h2 className="text-2xl font-bold mb-6 text-center" data-testid="mode-selection-title">Connect with your partner</h2>

              <div className="space-y-4">
                <Button
                  data-testid="create-code-button"
                  onClick={() => {
                    setMode('create');
                    handleGenerateCode();
                  }}
                  className="w-full bg-[#FFE270] hover:bg-[#ffd960] text-[#121212] border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
                >
                  Create Pairing Code
                </Button>

                <Button
                  data-testid="join-code-button"
                  onClick={() => {
                    setMode('join');
                    setStep('join');
                  }}
                  className="w-full bg-[#BEE3F8] hover:bg-[#a8d3e8] text-[#121212] border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
                >
                  Join with Code
                </Button>
              </div>
            </>
          )}

          {step === 'waiting' && (
            <>
              <h2 className="text-2xl font-bold mb-4 text-center" data-testid="pairing-code-title">Your Pairing Code</h2>
              <p className="text-[#52525B] text-center mb-6">Share this code with your partner</p>

              <div className="bg-[#FFE270] border-2 border-[#121212] rounded-2xl p-8 text-center mb-6 neo-brutal-shadow">
                <div className="text-5xl font-bold tracking-widest" data-testid="generated-code">{generatedCode}</div>
              </div>

              <Button
                data-testid="complete-pairing-button"
                onClick={onComplete}
                className="w-full bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
              >
                Done
              </Button>
            </>
          )}

          {step === 'join' && (
            <>
              <h2 className="text-2xl font-bold mb-4 text-center" data-testid="join-code-title">Enter Pairing Code</h2>
              <p className="text-[#52525B] text-center mb-6">Enter the 6-digit code from your partner</p>

              <div className="space-y-4">
                <Input
                  data-testid="pair-code-input"
                  placeholder="000000"
                  value={pairCode}
                  onChange={(e) => setPairCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyPress={(e) => e.key === 'Enter' && handleJoinCode()}
                  maxLength={6}
                  className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 focus-visible:bg-[#FFF9F0] neo-brutal-shadow text-3xl text-center font-bold p-6 tracking-widest"
                />

                <Button
                  data-testid="join-button"
                  onClick={handleJoinCode}
                  disabled={pairCode.length !== 6}
                  className="w-full bg-[#BEE3F8] hover:bg-[#a8d3e8] text-[#121212] border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
                >
                  Join
                </Button>

                <Button
                  data-testid="back-button"
                  onClick={() => setStep('mode')}
                  variant="outline"
                  className="w-full border-2 border-[#121212] rounded-xl py-6 text-lg font-bold bg-white hover:bg-[#FFF9F0] neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
                >
                  Back
                </Button>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
