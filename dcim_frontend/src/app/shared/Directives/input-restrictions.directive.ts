import { Directive,ElementRef,Input,HostListener } from '@angular/core';
@Directive({
  selector: '[appAppInputRestriction]',
  standalone: true
})
export class InputRestrictionDirective {

  inputElement: ElementRef;

  @Input('appAppInputRestriction')
  appAppInputRestriction!: string;
  arabicRegex = '[\u0600-\u06FF]';

  constructor(el: ElementRef) {
    this.inputElement = el;
  }

  @HostListener('keypress', ['$event']) onKeyPress(event: any) {
    this.notAllowSpaceatFirst(event)
  }

  integerOnly(event: any) {
    const e = <KeyboardEvent>event;
    if (e.key === 'Tab' || e.key === 'TAB') {
      return;
    }
    if ([46, 8, 9, 27, 13, 110].indexOf(e.keyCode) !== -1 ||
      // Allow: Ctrl+A
      (e.keyCode === 65 && e.ctrlKey === true) ||
      // Allow: Ctrl+C
      (e.keyCode === 67 && e.ctrlKey === true) ||
      // Allow: Ctrl+V
      (e.keyCode === 86 && e.ctrlKey === true) ||
      // Allow: Ctrl+X
      (e.keyCode === 88 && e.ctrlKey === true)) {
      // let it happen, don't do anything
      return;
    }
    if (['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'].indexOf(e.key) === -1) {
      e.preventDefault();
    }
  }

  noSpecialChars(event: any) {
    const e = <KeyboardEvent>event;
    if (e.key === 'Tab' || e.key === 'TAB') {
      return;
    }
    let k;
    k = event.keyCode;  // k = event.charCode;  (Both can be used)
    if ((k > 64 && k < 91) || (k > 96 && k < 123) || k === 8 || k === 32 || (k >= 48 && k <= 57)) {
      return;
    }
    const ch = String.fromCharCode(e.keyCode);
    const regEx = new RegExp(this.arabicRegex);
    if (regEx.test(ch)) {
      return;
    }
    e.preventDefault();
  }

  onlyChars(event: any) {
    const e = <KeyboardEvent>event;
    if (e.key === 'Tab' || e.key === 'TAB') {
      return;
    }
    let k;
    k = event.keyCode;  // k = event.charCode;  (Both can be used)
    if ((k > 64 && k < 91) || k === 8 || k === 32 || (k > 96 && k < 124)) {
      return;
    }
    e.preventDefault();
  }

  allowDecimal(event: any) {
    const e = <KeyboardEvent>event;

    if (e.key === 'Tab' || e.key === 'TAB') {
      return;
    }

    let k;

    k = event.keyCode;  // k = event.charCode;  (Both can be used)

    if ((k == 48) || (k == 49) || (k == 50) || (k == 51) ||
      (k == 52) || (k == 53) || (k == 54) || (k == 55) ||
      (k == 56) || (k == 57)) {
      var arcontrol = new Array();
      var temp = this.inputElement.nativeElement.value;
      arcontrol = this.inputElement.nativeElement.value.split(".");

      if (arcontrol.length == 1) {
        if (arcontrol[0].length < 16) {
          // event.returnValue=true;
          return;
        }
        else {
          // event.returnValue=false;
          // e.preventDefault();
        }
      }
      else {
        return;
      }
    }
    else if (k == 46) {
      var sCount = new Array();
      sCount = this.inputElement.nativeElement.value.split(".");

      if ((sCount.length) - 1 == 1) {
        // event.returnValue=false;
        // e.preventDefault();
      }
      else {
        // event.returnValue=true;
        return;
      }
    }

    e.preventDefault();
  }

  companyNameFormat(event: any) {
    const charCode = event.keyCode; 
    if (charCode == 46 || charCode == 38) {
      return ;
    }
    else {
      if ((charCode > 63 && charCode < 91) || (charCode > 96 && charCode < 123) || charCode == 8 || charCode == 32 || (charCode >= 48 && charCode <= 57)) {
        return ;
      }
      event.preventDefault();
    }
  }

  adressFormat(event: any) {
    const charCode =  event.keyCode; 
    if (charCode == 46 || charCode == 38 || charCode == 44 || charCode == 47 || charCode == 45) {
      return;
    }
    else {
      if ((charCode > 63 && charCode < 91) || (charCode > 96 && charCode < 123) || charCode == 8 || charCode == 32 || (charCode >= 48 && charCode <= 57)) {
        return;
      }
      event.preventDefault();
    }
  }
  notAllowSpaceatFirst(event: any) {
    if (event.target.selectionStart === 0 && event.code === "Space") {
      event.preventDefault();
    }
    else {
      var inputValue = event.charCode;
      // if (!(inputValue >= 65 && inputValue <= 120) && (inputValue != 32 && inputValue != 0)) {
      //   event.preventDefault();
      // }
      if (this.appAppInputRestriction === 'integer') {
        // this.notAllowSpaceatFirst(event)
        this.integerOnly(event);
      } else if (this.appAppInputRestriction === 'noSpecialChars') {
        // this.notAllowSpaceatFirst(event)
        this.noSpecialChars(event);
      }
      else if (this.appAppInputRestriction === 'onlyChars') {
        // this.notAllowSpaceatFirst(event)
        this.onlyChars(event);        
      }
      else if (this.appAppInputRestriction === 'allowDecimal') {
        // this.notAllowSpaceatFirst(event)
        this.allowDecimal(event);
      }else if(this.appAppInputRestriction === 'notZeroAtStart'){
        if (event.target.selectionStart === 0 && event.keyCode === 48) {
          alert('Credit limit should be greater than 0')
          event.preventDefault();
        }
      }else if(this.appAppInputRestriction === 'notOneoAtStart'){
        if (event.target.selectionStart === 0 && event.keyCode === 48) {
          alert('Quantity can not be 0')
          event.preventDefault();
        }
      }
    }
  }

}
