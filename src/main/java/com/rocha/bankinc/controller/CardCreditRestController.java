package com.rocha.bankinc.controller;

import java.util.*;

import com.rocha.bankinc.entity.Person;
import com.rocha.bankinc.repository.CardCreditRepository;
import com.rocha.bankinc.repository.PersonRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.rocha.bankinc.entity.CardCredit;

//Indiciamos que es un controlador rest
@RestController
@RequestMapping("/card") //esta sera la raiz de la url, es decir http://localhost:8080/card/

public class CardCreditRestController {

    @Autowired
    private CardCreditRepository cardCreditRepository;

    @Autowired
    private PersonRepository personRepository;




    @GetMapping("/{productId}/number")
    public CardCredit getCardCreditCreated(@PathVariable int productId){
        CardCredit cardCredit = new CardCredit();
        List<Person> personList = personRepository.findByProductId(productId);
        if(personList.isEmpty()){

            return cardCredit;
        }
        Person person = personList.getFirst();

        Random random = new Random();
        long randomNumber = random.nextLong();
        String stringNumber = Long.toString(randomNumber);

        while (stringNumber.length() < 10) {
            stringNumber = "0" + stringNumber;
        }
        stringNumber = String.valueOf(person.getProductId()) + stringNumber;

        Date currentDate = new Date();
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(currentDate);

        calendar.add(Calendar.YEAR, 3);

        int newMonth = calendar.get(Calendar.MONTH) + 1; // Months are 0-indexed, so add 1
        int newYear = calendar.get(Calendar.YEAR);


        cardCredit.setName(person.getName());
        cardCredit.setCardId(stringNumber);
        cardCredit.setDateExpires(String.valueOf(newMonth) + "/" + String.valueOf(newYear));
        cardCredit.setStatus(0);
        cardCredit.setBalance(100);
        cardCredit.setCreatedAt(currentDate);
        cardCredit.setUpdatedAt(currentDate);

        cardCreditRepository.save(cardCredit);

        return cardCredit;
    }

    @PostMapping("/enroll")
    public CardCredit addCardActive(@RequestBody CardCredit cardCredit) {

        CardCredit cardCreditResponse = cardCreditRepository.findByCardId(cardCredit.getCardId());
        cardCreditResponse.setStatus(1);
        cardCreditRepository.save(cardCreditResponse);
        return cardCreditResponse;

    }

    @DeleteMapping({"/{cardId}"})
    public CardCredit deleteCard(@PathVariable("cardId") String cardId) {
        CardCredit cardCreditResponse = cardCreditRepository.findByCardId(cardId);
        cardCreditResponse.setStatus(2);
        cardCreditRepository.save(cardCreditResponse);
        return cardCreditResponse;
    }

    @PostMapping("/balance")
    public CardCredit addCardBalance(@RequestBody CardCredit cardCredit) {

        CardCredit cardCreditResponse = cardCreditRepository.findByCardId(cardCredit.getCardId());
        cardCreditResponse.setBalance(cardCredit.getBalance());
        cardCreditRepository.save(cardCreditResponse);
        return cardCreditResponse;

    }

    @GetMapping("/balance/{cardId}")
    public String getCardIdBalance(@PathVariable("cardId") String cardId){

        CardCredit cardCreditResponse = cardCreditRepository.findByCardId(cardId);
        return "{ \"balance\": " + String.valueOf(cardCreditResponse.getBalance()) + "}";
    }

    @GetMapping("/cardCredits")
    public List<CardCredit> findAll(){

        return cardCreditRepository.findAll();
    }

}
