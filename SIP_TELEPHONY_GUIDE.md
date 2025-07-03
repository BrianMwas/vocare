# 📞 SIP Telephony Setup Guide

## 🎯 **Complete Call Flow Demo**

This guide shows how to set up the complete telephony system where customers can call a real phone number and talk to your AI restaurant assistant.

## 🏗️ **System Architecture**

```
📱 Customer Phone → 📡 SIP Provider → 🔄 FreeSWITCH → 🎙️ LiveKit → 🤖 AI Agent → 🔥 Firebase
```

### **Components:**
1. **FreeSWITCH**: SIP server (handles phone calls)
2. **LiveKit**: Media processing (handles audio/AI integration)  
3. **Your AI Agents**: Conversation logic
4. **Firebase**: Data persistence

## 🚀 **Local Development Setup**

### **1. Start All Services**

```bash
# Start the complete stack
docker-compose up -d

# Check all services are running
docker-compose ps
```

You should see:
- ✅ `freeswitch` (SIP server)
- ✅ `livekit` (Media server) 
- ✅ `backend` (Your AI assistant)

### **2. Test SIP Connection**

```bash
# Test FreeSWITCH is responding
telnet localhost 8021

# You should see FreeSWITCH Event Socket
```

### **3. Test AI Assistant**

```bash
# Check your assistant logs
docker-compose logs -f backend
```

## 📞 **Testing the Complete Flow**

### **Option 1: SIP Client Testing**

Use a SIP client like:
- **Zoiper** (mobile/desktop)
- **Linphone** (open source)
- **X-Lite** (desktop)

**SIP Settings:**
- **Server**: `your-server-ip:5060`
- **Username**: `restaurant` 
- **Password**: `1234` (development)

### **Option 2: PSTN Testing (Production)**

For real phone numbers, you need a SIP provider:
- **Twilio** (most popular)
- **Bandwidth**
- **Vonage**

**Example Twilio Setup:**
```yaml
# In freeswitch-config/freeswitch.xml
<gateway name="twilio">
  <param name="username" value="your-twilio-username"/>
  <param name="password" value="your-twilio-password"/>
  <param name="realm" value="your-twilio-realm.pstn.twilio.com"/>
  <param name="proxy" value="your-twilio-realm.pstn.twilio.com"/>
  <param name="register" value="true"/>
</gateway>
```

## 🔧 **Configuration Details**

### **FreeSWITCH Configuration**

**Key files:**
- `freeswitch-config/freeswitch.xml` - Main config
- `freeswitch-config/vars.xml` - Variables

**Important settings:**
```xml
<!-- Routes calls to your AI assistant -->
<extension name="restaurant-assistant">
  <condition field="destination_number" expression="^(restaurant|1234567890)$">
    <action application="socket" data="127.0.0.1:8080 async full"/>
  </condition>
</extension>
```

### **LiveKit Configuration**

**File**: `livekit-config.yaml`

**Key settings:**
```yaml
# SIP integration
sip:
  outbound_address: "freeswitch:5060"
  
# Room auto-creation
room:
  auto_create: true
```

### **Your AI Assistant**

**File**: `main.py`

**Key features:**
```python
# Detects SIP vs web calls
is_sip_call = ctx.job.job_type == "sip_call"

# Handles caller information
if is_sip_call:
    sip_ctx = SipContext(ctx)
    caller_number = sip_ctx.call_info.from_number
```

## 🌐 **Production Deployment (Google Cloud)**

### **1. Google Cloud Setup**

```bash
# Create VM instance
gcloud compute instances create restaurant-ai \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-standard-2 \
  --zone=us-central1-a

# Open firewall ports
gcloud compute firewall-rules create sip-ports \
  --allow tcp:5060,tcp:8021,udp:5060,udp:16384-16394 \
  --source-ranges 0.0.0.0/0
```

### **2. Deploy with Docker**

```bash
# SSH to your VM
gcloud compute ssh restaurant-ai

# Clone your repo
git clone https://github.com/yourusername/vocare.git
cd vocare

# Set up environment
cp .env.example .env
# Edit .env with production API keys

# Add Firebase service account
# Upload service.json

# Start production stack
docker-compose -f docker-compose.prod.yml up -d
```

### **3. Configure SIP Provider**

**Twilio Example:**
1. Buy a phone number in Twilio Console
2. Set webhook URL to your server
3. Configure SIP domain
4. Update FreeSWITCH gateway settings

## 🧪 **Testing Your Setup**

### **1. End-to-End Call Test**

```bash
# Call your restaurant number
# Should hear: "Hello! Welcome to Bella's Italian Kitchen..."

# Test conversation flow:
Customer: "I'd like to place an order"
AI: "Great! What would you like to order today?"
Customer: "I'll have a Margherita pizza"
AI: "Perfect! One Margherita pizza. Can I get your name?"
# ... continues through order flow
```

### **2. Check Logs**

```bash
# AI Assistant logs
docker-compose logs backend

# FreeSWITCH logs  
docker-compose logs freeswitch

# LiveKit logs
docker-compose logs livekit
```

### **3. Verify Data Flow**

```bash
# Check Firebase for order data
make list-menu

# Check call logs in Firebase
# Should see customer orders/reservations
```

## 🔍 **Debugging Common Issues**

### **SIP Registration Issues**
```bash
# Check FreeSWITCH status
docker exec -it vocare_freeswitch_1 fs_cli -x "sofia status"

# Check gateway registration
docker exec -it vocare_freeswitch_1 fs_cli -x "sofia status gateway"
```

### **Audio Issues**
```bash
# Check LiveKit room status
curl http://localhost:7880/rooms

# Check codec compatibility
# Ensure PCMU/PCMA are supported
```

### **AI Agent Issues**
```bash
# Check agent logs
docker-compose logs backend | grep -i error

# Test agent directly
python main.py
```

## 📊 **Monitoring & Analytics**

### **Key Metrics to Track:**
- **Call volume** (calls per hour/day)
- **Call duration** (average conversation length)
- **Order conversion** (calls that result in orders)
- **Agent performance** (handoff success rate)
- **Customer satisfaction** (if you implement ratings)

### **Firebase Analytics:**
```javascript
// Example queries in Firebase console
// 1. Orders by hour
// 2. Most popular menu items  
// 3. Average call duration
// 4. Customer repeat rate
```

## 🚨 **Security Considerations**

### **Production Security:**
1. **Change default passwords**
2. **Use HTTPS/WSS for LiveKit**
3. **Firewall rules** (limit SIP access)
4. **API key rotation**
5. **Call recording compliance** (if enabled)

### **GDPR/Privacy:**
- Inform callers about AI assistance
- Handle voice data according to regulations
- Implement data retention policies

## 📞 **Next Steps**

1. **Test locally** with SIP client
2. **Deploy to Google Cloud**  
3. **Configure SIP provider**
4. **Get real phone number**
5. **Test end-to-end calls**
6. **Monitor and optimize**

---

## 🎉 **You're Now Ready!**

Your restaurant can now receive real phone calls and handle them with AI assistants that:
- ✅ Answer in natural voice
- ✅ Take orders intelligently  
- ✅ Make reservations
- ✅ Store data in Firebase
- ✅ Provide excellent customer service

**Call flow demo complete!** 📞→🤖→🔥