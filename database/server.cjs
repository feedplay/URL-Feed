require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 4000;

// MongoDB Connection
const MONGO_URI = process.env.MONGO_URI;
mongoose.connect(MONGO_URI, { 
    useNewUrlParser: true, 
    useUnifiedTopology: true 
})
.then(() => console.log("✅ MongoDB Atlas Connected"))
.catch(err => {
    console.error("❌ MongoDB Connection Error:", err);
    process.exit(1); // Exit the process if connection fails
});

// More permissive CORS configuration
app.use(cors({
    origin: [
        'http://localhost:5173',  // Vite default port
        'http://localhost:3000',  // Create React App default port
        'http://127.0.0.1:5173'   // Alternative localhost address
    ],
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Logging middleware for debugging
app.use((req, res, next) => {
    console.log(`Received ${req.method} request to ${req.path}`);
    console.log('Request Headers:', req.headers);
    console.log('Request Body:', req.body);
    next();
});

// Define Schema & Model
const EmailSchema = new mongoose.Schema({ 
    email: { 
        type: String, 
        required: true,
        unique: true,
        trim: true,
        lowercase: true 
    },
    createdAt: { 
        type: Date, 
        default: Date.now 
    }
});

const Email = mongoose.model('Email', EmailSchema);

// API to store email
app.post('/api/store-email', async (req, res) => {
    console.log("📩 Detailed Request received:", req.body);

    const { email } = req.body;
    
    // Extensive validation
    if (!email) {
        console.error("❌ No email provided");
        return res.status(400).json({ error: "Email is required" });
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        console.error("❌ Invalid email format:", email);
        return res.status(400).json({ error: "Invalid email format" });
    }

    try {
        // Check if email already exists
        const existingEmail = await Email.findOne({ email });
        if (existingEmail) {
            console.log("⚠️ Email already exists:", email);
            return res.status(409).json({ message: "Email already exists" });
        }

        // Create and save new email
        const newEmail = new Email({ email });
        await newEmail.save();
        
        console.log("✅ Email successfully stored:", email);
        res.status(201).json({ 
            message: "Email stored successfully", 
            email: newEmail.email 
        });
    } catch (error) {
        console.error("❌ Complete Error Details:", error);
        
        // More granular error handling
        if (error.code === 11000) {
            return res.status(409).json({ 
                error: "Duplicate email", 
                details: "This email is already registered" 
            });
        }
        
        res.status(500).json({ 
            error: "Database storage error", 
            details: error.message 
        });
    }
});

// Fetch all stored emails (optional, for debugging)
app.get('/api/emails', async (req, res) => {
    try {
        const emails = await Email.find();
        res.json(emails);
    } catch (error) {
        console.error("❌ Error fetching emails:", error);
        res.status(500).json({ error: "Could not fetch emails" });
    }
});

// Global error handler
app.use((err, req, res, next) => {
    console.error("🚨 Unhandled Error:", err);
    res.status(500).json({ 
        error: "Unexpected server error", 
        message: err.message 
    });
});

// Start Server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Server running at http://localhost:${PORT}`);
});