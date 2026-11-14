import { useEffect,useRef,useState,type FormEvent } from 'react';
import { Link,Navigate,useLocation,useNavigate,useSearchParams } from 'react-router-dom';
import { ArrowLeft,ArrowRight,Check,CheckCircle2,Eye,EyeOff,LoaderCircle,LockKeyhole,Mail,ShieldCheck } from 'lucide-react';
import { applyActionCode,confirmPasswordReset,createUserWithEmailAndPassword,getMultiFactorResolver,GoogleAuthProvider,reload,sendEmailVerification,sendPasswordResetEmail,signInWithEmailAndPassword,signInWithPopup,signOut,TotpMultiFactorGenerator,updateProfile,validatePassword,verifyPasswordResetCode,type MultiFactorError,type MultiFactorResolver,type User } from '@firebase/auth';
import { Brand,Button } from '../components/ui';
import PromiseConversation from '../components/PromiseConversation';
import { useAuth } from '../state/Auth';
import { authMessage,firebaseAuth,safeReturnTo } from '../api/account';
import { PASSWORD_MIN_LENGTH,PASSWORD_MAX_LENGTH,PASSWORD_LENGTH_DESCRIPTION,passwordLengthAllowed } from '../api/password-policy';
import '../auth.css';
export function GoogleMark(){return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2.1H12v4h5.4a4.6 4.6 0 0 1-2 3v2.5h3.3c1.9-1.8 2.9-4.3 2.9-7.4"/><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.4L15.4 17c-.9.6-2 .9-3.4.9-2.6 0-4.9-1.8-5.7-4.2H2.9v2.6A10 10 0 0 0 12 22"/><path fill="#FBBC05" d="M6.3 13.7a6 6 0 0 1 0-3.4V7.7H2.9a10 10 0 0 0 0 8.6z"/><path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.9 1.5l2.9-2.9A10 10 0 0 0 2.9 7.7l3.4 2.6A6 6 0 0 1 12 6"/></svg>;}
export function PasswordField({value,onChange,label='Password',newPassword=false}:{value:string;onChange:(s:string)=>void;label?:string;newPassword?:boolean}){const [show,setShow]=useState(false);return <label className="auth-field"><span>{label}</span><span className="auth-password"><input aria-label={label} type={show ? 'text' : 'password'} autoComplete={newPassword ? 'new-password' : 'current-password'} value={value} onChange={e=>onChange(e.target.value)} required minLength={newPassword ? PASSWORD_MIN_LENGTH : 1} maxLength={PASSWORD_MAX_LENGTH}/><button type="button" aria-label={show ? 'Hide password' : 'Show password'} aria-pressed={show} onClick={()=>setShow(!show)}>{show ? <EyeOff size={18}/> : <Eye size={18}/>}</button></span></label>;}
export default function AuthPage(){
  const account=useAuth(),navigate=useNavigate(),location=useLocation(),[params]=useSearchParams();
  const isRegister=location.pathname==='/register',isForgot=location.pathname==='/forgot-password',isAction=location.pathname==='/auth/action',reauth=params.get('reauth')==='1';
  const target=safeReturnTo(params.get('returnTo'));
  const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[name,setName]=useState(''),[confirm,setConfirm]=useState(''),[code,setCode]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[pendingUser,setPendingUser]=useState<User|null>(null),[resolver,setResolver]=useState<MultiFactorResolver|null>(null),[factor,setFactor]=useState('');
  const [resetReady,setResetReady]=useState(false),[actionDone,setActionDone]=useState(false),[clientReady,setClientReady]=useState(false);
  useEffect(()=>{if(!account.config?.configured)return;let active=true;void firebaseAuth(account.config).then(()=>{if(active)setClientReady(true);}).catch(cause=>{if(active)setError(authMessage(cause));});return()=>{active=false;};},[account.config]);
  useEffect(()=>{setError('');setNotice(params.has('securityUpdated') ? 'Your security settings changed. Sign in again to continue.' : '');setPassword('');setConfirm('');setResolver(null);setPendingUser(null);},[location.pathname]);
  const actionOperation=useRef<{key:string;promise:Promise<{kind:'verified'|'reset';email?:string}>}|null>(null);
  useEffect(()=>{
    if(!isAction || !account.config?.configured)return;
    let active=true;const oob=params.get('oobCode') ?? '',mode=params.get('mode'),key=`${mode}:${oob}`;
    if(actionOperation.current?.key!==key){
      const promise=(async()=>{const auth=await firebaseAuth(account.config!);if(mode==='verifyEmail'){await applyActionCode(auth,oob);return {kind:'verified' as const};}if(mode==='resetPassword')return {kind:'reset' as const,email:await verifyPasswordResetCode(auth,oob)};throw new Error('This account link is not supported. Request a new email.');})();
      actionOperation.current={key,promise};
    }
    setBusy(true);setResetReady(false);setActionDone(false);
    void actionOperation.current.promise.then(result=>{if(!active)return;if(result.kind==='verified'){setActionDone(true);setNotice('Your email is verified. You can now sign in.');}else{setEmail(result.email!);setResetReady(true);}}).catch(cause=>{if(active)setError(authMessage(cause));}).finally(()=>{if(active)setBusy(false);});
    return()=>{active=false;};
  },[isAction,account.config,params]);
  async function finish(user:User){setPassword('');setConfirm('');if(!user.emailVerified){setPendingUser(user);setEmail(user.email ?? email);setNotice('Check your inbox for a verification link. Verify your email before opening your records.');return;}await account.complete(user);setPassword('');navigate(target,{replace:true});}
  async function attempt(action:()=>Promise<void>){if(busy)return;setBusy(true);setError('');setNotice('');try{await action();}catch(cause){if((cause as {code?:string}).code==='auth/multi-factor-auth-required' && account.config){const auth=await firebaseAuth(account.config),r=getMultiFactorResolver(auth,cause as MultiFactorError);const hints=r.hints.filter(h=>h.factorId===TotpMultiFactorGenerator.FACTOR_ID);if(!hints.length){setError('This account requires an unsupported second factor. Contact the project owner.');}else{setResolver(r);setFactor(hints[0].uid);setPassword('');setCode('');}}else{if((cause as {code?:string}).code==='RECENT_LOGIN_REQUIRED'){setPendingUser(null);setResolver(null);}setError(authMessage(cause));}}finally{setBusy(false);}}
  async function submit(event:FormEvent){event.preventDefault();await attempt(async()=>{
    if(!account.config)throw new Error('Sign-in is still loading. Please try again.');const auth=await firebaseAuth(account.config);
    if(resolver){await finish((await resolver.resolveSignIn(TotpMultiFactorGenerator.assertionForSignIn(factor,code))).user);return;}
    if(isForgot){try{await sendPasswordResetEmail(auth,email.trim(),{url:window.location.origin+'/login'});}catch(cause){if(!['auth/user-not-found','auth/invalid-email'].includes((cause as {code:string}).code))throw cause;}setNotice('If this email can receive a password reset, a link is on its way. Check your inbox and spam folder.');return;}
    if(isAction && resetReady){if(password!==confirm)throw new Error('The passwords do not match.');if(!passwordLengthAllowed(password) || !(await validatePassword(auth,password)).isValid)throw new Error(`Use ${PASSWORD_LENGTH_DESCRIPTION} and meet the password requirements.`);await confirmPasswordReset(auth,params.get('oobCode') ?? '',password);setPassword('');setConfirm('');setActionDone(true);setNotice('Your password has been updated. Sign in with your new password.');return;}
    if(isRegister){if(password!==confirm)throw new Error('The passwords do not match.');if(!passwordLengthAllowed(password) || !(await validatePassword(auth,password)).isValid)throw new Error(`Use ${PASSWORD_LENGTH_DESCRIPTION} and meet the password requirements.`);const user=(await createUserWithEmailAndPassword(auth,email.trim(),password)).user;setPassword('');setConfirm('');setPendingUser(user);await updateProfile(user,{displayName:name.trim()});await sendEmailVerification(user,{url:window.location.origin+'/login'});await finish(user);return;}
    await finish((await signInWithEmailAndPassword(auth,email.trim(),password)).user);
  });}
  const isVerify=Boolean(pendingUser),isMfa=Boolean(resolver),isReset=isAction&&resetReady&&!actionDone;
  const title=isMfa ? 'One more check.' : isVerify ? 'Check your inbox.' : isAction ? isReset ? 'A fresh start.' : 'Your account, confirmed.' : isForgot ? 'Let’s get you back in.' : isRegister ? 'A place for every promise.' : reauth ? 'Verify it’s you.' : 'Welcome back.';
  if(account.status==='signed-in' && !reauth && !isAction)return <Navigate to={target} replace/>;
  return <div className="auth-page landing">
    <a className="skip-link" href="#auth-form">Skip to account form</a>
    <header className="site-header"><div className="container header-inner"><Link to="/" aria-label="Bindr home"><Brand/></Link><Link to="/" className="header-cta"><ArrowLeft size={17}/>Back to Bindr</Link></div></header>
    <main className="auth-content container">
      <aside className="auth-welcome" aria-label="Keep your promises together">
        <span className="consumer-tag"><span/>For the follow-through.</span>
        <h2>Your promises.<br/><span>All in one place.<svg viewBox="0 0 390 15" aria-hidden="true"><path d="M4 10Q180 -1 386 7"/></svg></span></h2>
        <p>Your proof, dates and next steps, together.</p>
        <div className="auth-illustration"><PromiseConversation/></div>
      </aside>
      <section className="auth-panel" aria-labelledby="auth-title">
        <div id="auth-form" className="auth-form-wrap" tabIndex={-1}><h1 id="auth-title">{title}</h1><p className="auth-intro">{isMfa ? 'Enter the six-digit code from your authenticator app.' : isVerify ? `We sent a verification link to ${email}.` : isReset ? 'Choose a strong password you haven’t used elsewhere.' : isForgot ? 'Enter your email and we’ll send you a reset link.' : isAction ? 'Secure access to the promises you keep on record.' : isRegister ? 'Keep your proof and deadlines together, on every device.' : reauth ? 'Sign in again to change your account security.' : 'Sign in to pick up where you left off.'}</p>
    {account.status==='loading' && <p className="auth-notice" role="status"><LoaderCircle className="spin" size={18}/>Preparing secure sign-in…</p>}
    {(error || account.status==='unavailable') && <div className="auth-error" role="alert">{error || account.error}<button type="button" onClick={()=>window.location.reload()}>Reload</button></div>}
    {notice && <div className="auth-notice" role="status"><CheckCircle2 size={19}/><span>{notice}</span></div>}
    {isVerify ? <div className="auth-verify"><div className="auth-mail-art"><Mail size={32}/><Check size={17}/></div><Button disabled={busy} onClick={()=>void attempt(async()=>{await reload(pendingUser!);if(!pendingUser!.emailVerified)throw new Error('Your email is not verified yet. Open the link in your email, then try again.');await finish(pendingUser!);})}>I’ve verified my email <ArrowRight size={17}/></Button><Button variant="secondary" disabled={busy} onClick={()=>void attempt(async()=>{await sendEmailVerification(pendingUser!,{url:window.location.origin+'/login'});setNotice('A fresh verification link is on its way. Check your inbox and spam folder.');})}>Resend verification email</Button><button className="auth-text" onClick={()=>void attempt(async()=>{await signOut(await firebaseAuth(account.config!));setPendingUser(null);setNotice('');})}>Use another account</button></div> : actionDone ? <Link to="/login" className="button button-primary">Continue to sign in <ArrowRight size={17}/></Link> : <>
    {!isForgot && !isAction && !isMfa && <><Button variant="secondary" className="auth-google" disabled={busy || !clientReady} onClick={()=>void attempt(async()=>{const auth=await firebaseAuth(account.config!),provider=new GoogleAuthProvider();provider.setCustomParameters({prompt:'select_account'});await finish((await signInWithPopup(auth,provider)).user);})}><GoogleMark/>Continue with Google</Button><div className="auth-divider"><span/>or continue with email<span/></div></>}
    {(!isAction || isReset) && <form className="auth-form" onSubmit={submit}>
      {isMfa ? <><label className="auth-field"><span>Authenticator code</span><input className="auth-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,''))} required autoFocus/></label>{resolver!.hints.filter(h=>h.factorId==='totp').length>1 && <label className="auth-field"><span>Authenticator</span><select value={factor} onChange={e=>setFactor(e.target.value)}>{resolver!.hints.filter(h=>h.factorId==='totp').map(h=><option key={h.uid} value={h.uid}>{h.displayName || 'Authenticator app'}</option>)}</select></label>}<p className="auth-help">Use another enrolled authenticator if you cannot access your usual device. Password reset does not remove two-factor protection.</p></> : <>
      {isRegister && <label className="auth-field"><span>Your name</span><input autoComplete="name" value={name} onChange={e=>setName(e.target.value)} maxLength={100} required/></label>}
      {!isReset && <label className="auth-field"><span>Email address</span><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required maxLength={320} placeholder="you@example.com"/></label>}
      {!isForgot && <PasswordField value={password} onChange={setPassword} newPassword={isRegister||isReset}/>}
      {(isRegister||isReset) && <><p className="auth-help">{PASSWORD_LENGTH_DESCRIPTION}. A unique passphrase works well. Password managers and pasted passwords are welcome.</p><PasswordField value={confirm} onChange={setConfirm} label="Confirm password" newPassword/></>}
      {!isForgot && !isRegister && !isReset && <Link className="auth-forgot" to="/forgot-password">Forgot password?</Link>}</>}
      <Button type="submit" disabled={busy || !clientReady}>{busy ? <LoaderCircle className="spin" size={18}/> : isMfa ? <ShieldCheck size={18}/> : isForgot ? <Mail size={18}/> : <ArrowRight size={18}/>} {isMfa ? 'Verify and sign in' : isForgot ? 'Send reset link' : isReset ? 'Update password' : isRegister ? 'Create account' : 'Sign in'}</Button>
    </form>}
    <p className="auth-switch">{isForgot||isAction||isMfa ? <Link to="/login" onClick={()=>setResolver(null)}>Back to sign in</Link> : isRegister ? <>Already have an account? <Link to={`/login?returnTo=${encodeURIComponent(target)}`}>Sign in</Link></> : <>New to Bindr? <Link to={`/register?returnTo=${encodeURIComponent(target)}`}>Create an account</Link></>}</p></>}
    <p className="auth-private"><LockKeyhole size={14}/>Your records are private to your account.</p>
        </div>
      </section>
    </main>
    <footer className="auth-footer container"><span>Every promise. Every update. One record.</span><span>© {new Date().getFullYear()} Bindr</span></footer>
  </div>;
}
