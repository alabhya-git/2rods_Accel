import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './fonts'
import './index.css'
import { LangProvider } from './lib/i18n'
import Home from './screens/Home'
import Advisor from './screens/Advisor'
import Quote from './screens/Quote'
import Consent from './screens/Consent'
import Kyc from './screens/Kyc'
import Pay from './screens/Pay'
import Track from './screens/Track'
import Partner from './screens/Partner'
import Judge from './screens/Judge'
import WhatsApp from './screens/WhatsApp'
import Express from './screens/Express'
import Orders from './screens/Orders'
import Help from './screens/Help'
import SimVerify from './screens/SimVerify'
import Approve from './screens/Approve'
import VerifyCaller from './screens/VerifyCaller'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LangProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/advisor" element={<Advisor />} />
          <Route path="/quote" element={<Quote />} />
          <Route path="/order/:id/consent" element={<Consent />} />
          <Route path="/order/:id/kyc" element={<Kyc />} />
          <Route path="/order/:id/pay" element={<Pay />} />
          <Route path="/track/:id" element={<Track />} />
          <Route path="/partner" element={<Partner />} />
          <Route path="/judge" element={<Judge />} />
          <Route path="/whatsapp" element={<WhatsApp />} />
          <Route path="/express" element={<Express />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/help" element={<Help />} />
          <Route path="/sim/:id" element={<SimVerify />} />
          <Route path="/approve/:token" element={<Approve />} />
          <Route path="/verify" element={<VerifyCaller />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </LangProvider>
  </React.StrictMode>,
)
