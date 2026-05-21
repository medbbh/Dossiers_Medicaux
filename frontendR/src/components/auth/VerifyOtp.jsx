/* eslint-disable react/no-unescaped-entities */
/* eslint-disable no-unused-vars */
import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import AuthService from "../../services/AuthService";
import { useAuth } from "../../context/AuthContext";
import { FaCheckCircle } from 'react-icons/fa';
import { toast } from "react-hot-toast";

const VerifyOtp = () => {
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login, userRole } = useAuth();
  const email = location.state?.email || "";
  const testOtp = location.state?.otp || null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await AuthService.verifyOTP({ email, otp });
      const role = response.data.role; // Récupérer le rôle depuis la réponse de l'API
      login(response.data, role); // Passer le rôle à la fonction login

      // Rediriger en fonction du rôle de l'utilisateur
      if (role === "Admin") {
        navigate("/dashboard");
      } else if (role === "Doctor") {
        navigate("/home");
      } else {
        navigate("/");
      }
      toast.success("Connexion réussie !");
    } catch (error) {
      toast.error(
        error.response?.data?.error || "OTP invalide. Veuillez réessayer."
      );
    } finally {
      setIsLoading(false);
    }
  };

  

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-semibold text-center mb-6 flex items-center justify-center">
          <FaCheckCircle className="mr-2 text-green-500" />
          Vérification OTP
        </h2>
        <p className="text-center mb-4">Un code de vérification a été envoyé à {email}</p>

        {testOtp && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-center">
            <p className="text-xs text-yellow-700 font-medium mb-1">Test mode — OTP code:</p>
            <p className="text-2xl font-bold tracking-widest text-yellow-800">{testOtp}</p>
          </div>
        )}

        <div className="mb-4">
          <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2">
            Entrez l'OTP
          </label>
          <input
            type="text"
            id="otp"
            name="otp"
            placeholder="Entrez OTP"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            className="w-full p-3 border rounded-lg focus:outline-none focus:ring border-gray-300"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || otp.length === 0}
          className={`w-full p-3 rounded-lg text-white ${
            isLoading || otp.length === 0
              ? "bg-gray-300 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600"
          } flex items-center justify-center`}
        >
          {isLoading ? "Vérification en cours..." : (
            <>
              <FaCheckCircle className="mr-2" />
              Vérifier OTP
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default VerifyOtp;