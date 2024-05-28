package com.rocha.bankinc.controller;

import com.rocha.bankinc.entity.CardCredit;
import com.rocha.bankinc.entity.Person;
import com.rocha.bankinc.entity.Transaction;
import com.rocha.bankinc.repository.TransactionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Date;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/transaction")
public class TransactionController {

    @Autowired
    private TransactionRepository transactionRepository;

    @PostMapping("/purchase")
    public Transaction purchase(@RequestBody Transaction transaction) {

        transaction.setCreatedAt(new Date());
        transaction.setUpdatedAt(new Date());
        transaction.setStatus(1);
        return transactionRepository.save(transaction);
    }

    @PostMapping("/anulation")
    public Transaction anulation(@RequestBody Transaction transaction) {

        Transaction transactionL = transactionRepository.findByCardIdAndTransactionId(transaction.getCardId(), transaction.getTransactionId());


        transactionL.setUpdatedAt(new Date());
        transactionL.setStatus(2);

        return transactionRepository.save(transactionL);
    }

    @GetMapping("/all")
    public List<Transaction> findAll(){

        return transactionRepository.findAll();
    }

    @GetMapping("/{transactionId}")
    public Transaction findById(@PathVariable("transactionId") Long transactionId){


        Optional<Transaction> transaction = transactionRepository.findById(transactionId);

        return transaction.orElse(null);
    }
}
