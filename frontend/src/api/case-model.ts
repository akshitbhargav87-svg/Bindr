import type { CaseDetail, Commitment } from './types';
import type { CaseRow } from './mapper';
export interface CaseEvent {id:string;kind:'partial'|'pending'|'resolved'|'reopened'|'edited'|'archived'|'restored'|'claim'|'update'|'review';title:string;note:string;at:string;evidenceIds:string[];amountMinor:number|null}
export interface CaseExtras {archived:boolean;receivedMinor:number;partiallyFulfilled:boolean;events:CaseEvent[]}
export interface CaseView {detail:CaseDetail;row:CaseRow;meta:CaseExtras;totalMinor:number|null;outstandingMinor:number|null}
export interface TimelineItem {id:string;at:string;title:string;note:string;evidenceIds:string[];commitment?:Commitment;kind:'promise'|'evidence'|'event';amountMinor?:number|null}
export const emptyCaseExtras=():CaseExtras=>({archived:false,receivedMinor:0,partiallyFulfilled:false,events:[]});
