import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [partner, setPartner] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const userId = localStorage.getItem('userId');
    if (userId) {
      loadUser(userId);
    } else {
      setLoading(false);
    }
  }, []);

  const loadUser = async (userId) => {
    try {
      const { data } = await axios.get(`${API}/auth/me`, { params: { userId } });
      setUser(data);
      
      // Load partner
      const partnerRes = await axios.get(`${API}/auth/partner`, { params: { userId } });
      setPartner(partnerRes.data);
    } catch (error) {
      console.error('Failed to load user:', error);
      localStorage.removeItem('userId');
    } finally {
      setLoading(false);
    }
  };

  const createUser = async (name) => {
    const { data } = await axios.post(`${API}/auth/create-user`, { name });
    setUser(data);
    localStorage.setItem('userId', data.id);
    return data;
  };

  const generatePairCode = async () => {
    const { data } = await axios.post(`${API}/auth/generate-code`, null, {
      params: { userId: user.id }
    });
    return data.pairCode;
  };

  const joinCouple = async (pairCode) => {
    await axios.post(`${API}/auth/join-couple`, {
      pairCode,
      userId: user.id
    });
    await loadUser(user.id);
  };

  const logout = () => {
    localStorage.removeItem('userId');
    setUser(null);
    setPartner(null);
  };

  return (
    <AuthContext.Provider value={{ user, partner, loading, createUser, generatePairCode, joinCouple, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
